"""
Entry point for network_connection events.
Called from api/views.py when event_type == "network_connection".
Returns dict matching teammate's exact AnomalyResult format.
"""
import uuid
import logging
from datetime import datetime

from .network_features import extract
from .network_model import predict
from .network_scorer import verify

logger = logging.getLogger(__name__)

ATTACK_PORTS = {
    53:   ("DrDoS_DNS",  "T1498.002", "high"),
    123:  ("DrDoS_NTP",  "T1498.002", "high"),
    161:  ("DrDoS_SNMP", "T1498.002", "high"),
    389:  ("LDAP",       "T1498.002", "high"),
    1433: ("MSSQL",      "T1498.001", "critical"),
    1900: ("DrDoS_SSDP", "T1498.002", "high"),
    137:  ("NetBIOS",    "T1498.002", "high"),
    111:  ("Portmap",    "T1498.002", "high"),
    69:   ("TFTP",       "T1498.002", "medium"),
}


def handle_network_event(event: dict) -> dict:
    return handle_network_window([event])


def handle_network_window(events: list) -> dict:
    if not events:
        return _build_result(
            events=[], score=0.0, flagged=False,
            prediction={}, label="Normal",
            mitre=None, severity="none",
            scorer_rules=[]
        )

    first    = events[0]
    meta     = first.get("metadata", {})
    dst_port = int(meta.get("dst_port", 0) or 0)
    protocol = str(meta.get("protocol", "tcp") or "tcp").upper()

    # ── Extract features → run model ──────────────────────────────
    features = extract(events)
    try:
        prediction = predict(features)
    except Exception as e:
        logger.error(f"Network model prediction failed: {e}")
        return _build_result(
            events=events, score=0.0, flagged=False,
            prediction={}, label="Normal",
            mitre=None, severity="none",
            scorer_rules=[], error=str(e)
        )

    # ── Scorer verification ───────────────────────────────────────
    verification = verify(prediction, events)
    score        = verification["final_score"]
    flagged      = verification["final_flagged"]
    scorer_rules = verification["scorer_rules"]

    # ── Identify attack type ──────────────────────────────────────
    if flagged and dst_port in ATTACK_PORTS:
        label, mitre, severity = ATTACK_PORTS[dst_port]
    elif flagged:
        if protocol == "UDP":
            label, mitre, severity = "UDP_Flood",  "T1498.001", "high"
        else:
            label, mitre, severity = "Syn_Flood",  "T1498.001", "critical"
    else:
        label, mitre, severity = "Normal", None, "none"

    return _build_result(
        events=events, score=score, flagged=flagged,
        prediction=prediction, label=label,
        mitre=mitre, severity=severity,
        scorer_rules=scorer_rules
    )


# ── New helper function for dynamic explanation ───────────────────────────────
def _get_explanation(label: str, score: float, rules: list, meta: dict, prediction: dict) -> str:
    """Calls LLM explainer — falls back to template silently."""
    try:
        from .network_explainer import explain
        return explain(label, score, rules, meta, prediction)
    except Exception as e:
        logger.warning(f"LLM explainer failed: {e}")
        src  = meta.get('src_ip', '?')
        dst  = meta.get('dst_ip', '?')
        port = meta.get('dst_port', '')
        return (
            f"The hybrid model detected a {label} attack from {src} → {dst}:{port} "
            f"with score {score:.3f}. Signals: {', '.join(rules[:3])}."
        )

def _build_result(events, score, flagged, prediction,
                   label, mitre, severity,
                   scorer_rules=None, error=None) -> dict:

    if scorer_rules is None:
        scorer_rules = []

    first     = events[0] if events else {}
    meta      = first.get("metadata", {})
    user_id   = first.get("user_id",  "unknown")
    timestamp = first.get("timestamp", datetime.utcnow().isoformat())
    dst_port  = int(meta.get("dst_port", 0) or 0)

    # ── Build triggered rules ─────────────────────────────────────
    rules = []
    if prediction.get("stage1_flagged"):
        rules.append("isolation_forest_anomaly_detected")
    if prediction.get("cat_pred") == 1:
        rules.append("catboost_confirmed_attack")
    if prediction.get("stage1_flagged") and prediction.get("cat_pred") == 1:
        rules.append("both_stages_agree_high_confidence")
    if score >= 0.75:
        rules.append("high_confidence_detection")
    elif score >= 0.40:
        rules.append("medium_confidence_detection")
    if dst_port in ATTACK_PORTS:
        rules.append(f"known_attack_port_{dst_port}")
    if flagged:
        rules.append(f"network_attack_detected_{label.lower().replace('-', '_')}")

    # Append scorer verification rules
    rules.extend(scorer_rules)

    confidence = "high"   if score >= 0.75 else \
                 "medium" if score >= 0.40 else "low"
    verdict    = "CRITICAL" if score >= 0.85 else \
                 "HIGH"     if score >= 0.65 else \
                 "MEDIUM"   if score >= 0.40 else "NORMAL"

    return {
        "event_id":              str(uuid.uuid4()),
        "timestamp":             timestamp,
        "source":                ["network_agent"],
        "user_anomaly_score":    None,
        "network_anomaly_score": round(score, 4) if flagged else 0.0,
        "combined_score":        round(score, 4),
        "user_id":               user_id,
        "entity_id":             meta.get("src_ip", "unknown"),
        "dimension_scores": {
            "time":        0.0,
            "device":      0.0,
            "volume":      round(score, 4),
            "sensitivity": 0.0,
        },
        "triggered_rules":         rules,
        "network_attack_category": label if flagged else None,
        "correlation":             {},
        "explanation": (
            _get_explanation(label, score, rules, meta, prediction)
            if flagged else
            "Traffic classified as normal by hybrid network model."
        ),
        "baseline_age_days": 0,
        "confidence":        confidence,
        "cold_start":        False,
        "simulated":         meta.get("is_simulated", False),
        "flagged":           flagged,
        "if_score":          round(prediction.get("anomaly_score", 0), 4),
        "detection_agent_analysis": {
            "model":        "IF+CatBoost+LLM",
            "llm_used":     flagged,
            "analyst_note": error or "",
            "scoring_mode": "hybrid",
            "score":        round(score, 4),
            "threshold":    0.40,
            "verdict":      verdict,
            "triggered_signals": rules,
            "dimension_breakdown": {
                "time":        0.0,
                "device":      0.0,
                "volume":      round(score, 4),
                "sensitivity": 0.0,
            },
            "session_summary": {
                "src_ip":         meta.get("src_ip"),
                "dst_ip":         meta.get("dst_ip"),
                "dst_port":       dst_port,
                "protocol":       meta.get("protocol"),
                "bytes_sent":     meta.get("bytes_sent"),
                "bytes_received": meta.get("bytes_received"),
            },
            "baseline_context": {},
        },
    }
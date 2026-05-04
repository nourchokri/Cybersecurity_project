"""
Decision Agent (Motor) - Contextual Intelligence for SOC Pipeline

This is the Decision Agent in a multi-agent SOC system:
Team 1 (Collector) → Team 2 (Pattern Agent) → YOU (Decision Agent) → Team 4 (Reporting)

Your Value-Add:
- Contextual risk adjustment (beyond pattern scores)
- Adaptive decision-making (not static thresholds)
- Historical learning (from incident outcomes)
- Explainable reasoning (for SOC analysts)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import os
import shlex
import sys
import threading
import traceback
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timedelta

from .reasoning import LLMConfig, LLMReasoner
from ..skills import RiskComputationSkill
from ..infrastructure.cache.cache_manager import CacheManager, make_cache_key

try:
    from ..infrastructure.mcp.client import McpServerSpec, get_mcp_client
except Exception:  # pragma: no cover
    McpServerSpec = None  # type: ignore
    get_mcp_client = None  # type: ignore


# Resolve paths relative to this file's location.
_AGENT_ROOT = Path(__file__).resolve().parents[1]  # risk_decision_agent/
_MCP_SERVER_SCRIPT = str(_AGENT_ROOT / "infrastructure" / "mcp" / "server.py")
_DEFAULT_DATA_DIR = _AGENT_ROOT / "infrastructure" / "data" / "local_data"


class DecisionAgent:
    """
    Decision Agent (Motor) - Core intelligence of the SOC system

    Receives: Analyzed patterns from Team 2 (Pattern Agent)
    Provides: Contextual risk assessment + intelligent decision
    Outputs: Decision + explanation to Team 4 (Reporting Agent)
    """

    def __init__(
        self,
        llm: LLMReasoner,
        *,
        enable_caching: bool = True,
        cache_db_path: str = "decision_agent_cache.db",
        cache_ttl: int = 3600,
        data_dir: Optional[Path] = None,
        enable_llm_cache: bool = True,
        verbose: bool = True,
        mcp_server: str = "",
        mcp_timeout_sec: float = 30.0,
    ):
        # Tool calls are executed over real MCP (stdio) only.
        self.llm = llm
        self.verbose = verbose

        self.enable_caching = enable_caching
        self.enable_llm_cache = enable_llm_cache
        self._data_dir = Path(data_dir) if data_dir is not None else None
        self._data_signature: Optional[Tuple[float, ...]] = None

        self._mcp_timeout_sec = float(mcp_timeout_sec)
        default_server = f'"{sys.executable}" "{_MCP_SERVER_SCRIPT}"'
        self._mcp_server = (mcp_server or default_server).strip()
        self._mcp_client = None

        # SQLite-based cache manager (replaces in-memory dicts)
        if enable_caching:
            self.cache = CacheManager(db_path=cache_db_path, default_ttl=cache_ttl)
            self._print(f"[Cache] Using SQLite cache: {cache_db_path}")
        else:
            self.cache = None

        # Debug/telemetry: whether the most recent LLM analysis was served from cache.
        self._last_llm_cache_hit: bool = False
        self._last_tool_cache_hits: int = 0

        # Per-tool TTL overrides for the SQLite cache.
        self._tool_cache_ttls: Dict[str, int] = {
            "local_policy.get_thresholds": 86400,
            "cert.rule_library.explain": 86400,
            "cert.telemetry.get_file_metadata": 3600,
            "cert.identity.get_user_context": 3600,
            "cert.telemetry.get_user_baseline": 3600,
            "cert.telemetry.get_user_summary": 3600,
            "cert.telemetry.get_deviations": 3600,
        }

        # Python skills for deterministic scoring
        self.risk_skill = RiskComputationSkill()

    def _get_mcp_client(self):
        if get_mcp_client is None or McpServerSpec is None:
            raise RuntimeError(
                "MCP dependencies are not available. Install requirements (pip install -r requirements.txt) "
                "and re-run."
            )
        if self._mcp_client is not None:
            return self._mcp_client

        parts = shlex.split(self._mcp_server, posix=(os.name != "nt"))
        if not parts:
            raise ValueError("mcp_server is empty")

        def strip_quotes(s: str) -> str:
            s = (s or "").strip()
            if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
                return s[1:-1]
            return s

        cmd = strip_quotes(parts[0])
        args = tuple(strip_quotes(p) for p in parts[1:])
        self._mcp_client = get_mcp_client(
            server=McpServerSpec(command=cmd, args=args),
            timeout_sec=self._mcp_timeout_sec,
        )
        return self._mcp_client

    def _call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Call a tool via real MCP (stdio) with transparent SQLite caching."""
        args = args or {}

        cache_key: Optional[str] = None
        if self.enable_caching and self.cache:
            try:
                args_json = json.dumps(
                    args, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"),
                )
            except Exception:
                args_json = repr(args)

            args_hash = hashlib.sha256(args_json.encode("utf-8")).hexdigest()
            cache_key = make_cache_key("tool", tool_name, args_hash)

            cached = self.cache.get(cache_key)
            if cached is not None:
                self._last_tool_cache_hits += 1
                self._print(f"  [Tool] {tool_name} (cache hit)")
                return cached

        self._print(f"  [Tool] {tool_name}")
        client = self._get_mcp_client()
        result = client.call_tool(tool_name, args)

        # Ensure the result is JSON-serializable (MCP SDK may return raw objects).
        result = self._ensure_serializable(result)

        if self.enable_caching and self.cache and cache_key is not None:
            ttl = int(self._tool_cache_ttls.get(tool_name, getattr(self.cache, "default_ttl", 3600)))
            try:
                self.cache.set(cache_key, result, ttl=ttl)
            except Exception:
                pass

        return result

    @staticmethod
    def _ensure_serializable(obj: Any) -> Any:
        """Convert non-serializable MCP result objects to plain dicts/strings."""
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, (dict, list)):
            return obj
        # Try JSON round-trip
        try:
            return json.loads(json.dumps(obj, default=str))
        except Exception:
            return str(obj)

    def _print(self, *args: Any, **kwargs: Any) -> None:
        msg = " ".join(str(a) for a in args)
        if hasattr(self, "_local") and hasattr(self._local, "logs"):
            self._local.logs.append(msg)

        if self.verbose:
            try:
                print(*args, **kwargs)
            except UnicodeEncodeError:
                # Windows console may not support all characters.
                safe = " ".join(str(a).encode("ascii", "replace").decode() for a in args)
                print(safe, **kwargs)

    def _normalize_event(self, anomaly_event: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Team 2 event shape(s) into the schema used by this agent."""
        event_id = anomaly_event.get("event_id") or anomaly_event.get("id")

        score = anomaly_event.get("combined_score")
        if score is None:
            score = anomaly_event.get("score")

        dim_scores = anomaly_event.get("dimension_scores")
        if dim_scores is None:
            dim_scores = anomaly_event.get("dim_scores")

        triggered_rules = anomaly_event.get("triggered_rules")
        if triggered_rules is None:
            triggered_rules = anomaly_event.get("rules")
        if triggered_rules is None:
            triggered_rules = []

        normalized = dict(anomaly_event)
        normalized.update({
            "event_id": event_id,
            "combined_score": score,
            "dimension_scores": dim_scores,
            "triggered_rules": triggered_rules,
        })

        normalized.setdefault("if_score", anomaly_event.get("if_score"))
        normalized.setdefault("raw_features", anomaly_event.get("raw_features"))
        normalized.setdefault("monitor", anomaly_event.get("monitor"))
        normalized.setdefault("confidence", anomaly_event.get("confidence"))
        normalized.setdefault("cold_start", anomaly_event.get("cold_start", False))
        normalized.setdefault("threat_classification", anomaly_event.get("threat_classification", "unknown"))

        return normalized

    def decide(self, anomaly_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main decision method - receives event from Team 2, returns decision for Team 4.

        Process (demo flow):
        1. Gather context via MCP tools (cached in SQLite)
        2. LLM analyzes context and recommends a risk adjustment (cached)
        3. Python clamps/validates adjustment
        4. Choose a decision and build an explainable output
        """
        if not hasattr(self, "_local"):
            self._local = threading.local()
        self._local.logs = []

        event = self._normalize_event(anomaly_event)

        self._print("\n=== Decision Agent: Contextual Risk Analysis ===\n")
        self._print(f"Event ID: {event.get('event_id')}")
        self._print(f"Base Score (from Team 2): {event.get('combined_score')}")
        self._print(f"Threat Classification: {event.get('threat_classification')}")

        # Step 1: Gather context
        self._print("\n[ReAct] Gathering context...")
        context = self._react_gather_context(event)
        if self.enable_caching and self._last_tool_cache_hits > 0:
            self._print(f"[Cache] Used cached tool results ({self._last_tool_cache_hits} hit(s))")

        # Step 2: LLM analyzes context and recommends risk adjustment
        self._print("\n[LLM] Analyzing contextual risk...")
        try:
            contextual_analysis = self._analyze_contextual_risk_cached(
                event=event, context=context, language="en",
            )
            if self.enable_caching and self.enable_llm_cache and self._last_llm_cache_hit:
                self._print("  (cache hit)")
                self._print("[Cache] Used cached LLM analysis")
            self._print(f"  Risk factors: {len(contextual_analysis.get('risk_factors', []))}")
            self._print(f"  Mitigating factors: {len(contextual_analysis.get('mitigating_factors', []))}")
            self._print(f"  Recommended adjustment: {contextual_analysis.get('risk_adjustment', 0):+.2f}")
        except Exception as e:
            self._print(f"  [WARN] LLM analysis failed: {e}")
            contextual_analysis = {
                "base_score_analysis": "Analysis failed",
                "risk_factors": ["LLM analysis failed"],
                "mitigating_factors": [],
                "risk_adjustment": 0.0,
                "adjustment_reasoning": "Defaulting to base score",
                "recommended_decision": "MONITOR",
                "decision_reasoning": "Using base score due to analysis failure",
                "confidence": "low",
            }

        # Step 3: Apply bounded risk adjustment
        self._print("\n[Risk] Applying risk adjustment...")
        base_score = float(event.get("combined_score", 0) or 0)
        llm_adjustment = float(contextual_analysis.get("risk_adjustment", 0))

        validated_adjustment = max(-0.3, min(0.3, llm_adjustment))
        adjusted_risk = max(0.0, min(1.0, base_score + validated_adjustment))

        if abs(validated_adjustment - llm_adjustment) > 0.01:
            self._print(f"  [WARN] Clamped adjustment: {llm_adjustment:+.2f} -> {validated_adjustment:+.2f}")

        self._print(f"  Base score: {base_score:.2f}")
        self._print(f"  Adjustment: {validated_adjustment:+.2f}")
        self._print(f"  Adjusted risk: {adjusted_risk:.2f}")

        # Step 4: Determine risk level and decision
        thresholds = context.get("policy_thresholds", {"low_max": 0.4, "medium_max": 0.7})
        risk_level = self.risk_skill.classify_risk_level(adjusted_risk, thresholds)

        if contextual_analysis.get("confidence") == "high":
            decision = contextual_analysis.get("recommended_decision", "MONITOR")
        else:
            decision = self.risk_skill.generate_decision(
                risk_level, context.get("user"), context.get("asset")
            )

        # Apply Frequent Low-Level Offender penalty
        if decision in ("ALLOW", "MONITOR") and adjusted_risk > 0.3:
            if self.enable_caching and self.cache and event.get("user_id"):
                try:
                    is_repeat = self._check_and_update_low_level_offenses(
                        user_id=str(event.get("user_id")),
                        event_ts=event.get("timestamp"),
                        score=adjusted_risk,
                    )
                    if is_repeat:
                        self._print("  [WARN] Frequent low-level offender detected! Applying +0.3 penalty.")
                        adjusted_risk = min(1.0, adjusted_risk + 0.3)
                        risk_level = self.risk_skill.classify_risk_level(adjusted_risk, thresholds)
                        decision = "ESCALATE"
                        
                        # Add explanation to output
                        rf = contextual_analysis.get("risk_factors", [])
                        if isinstance(rf, list):
                            rf.append("Frequent low-level offender penalty applied (+0.3)")
                            contextual_analysis["risk_factors"] = rf
                        contextual_analysis["adjustment_reasoning"] = str(contextual_analysis.get("adjustment_reasoning", "")) + " | User had >3 low-level anomalous events today; forced escalation."
                except Exception as e:
                    self._print(f"  [WARN] Failed to process low-level offender cache: {e}")

        self._print(f"  Risk level: {risk_level}")
        self._print(f"  Decision: {decision}")

        # Persist incident signal
        if self.enable_caching and self.cache and event.get("user_id"):
            try:
                self._update_recent_incidents_cache(
                    user_id=str(event.get("user_id")),
                    decision=str(decision),
                    event_ts=event.get("timestamp"),
                )
            except Exception:
                pass

        # Step 5: Build final output
        asset_ctx = context.get("asset") or {}
        user_ctx = context.get("user") or {}
        incident_ctx = context.get("incident_history") or {}

        asset_sensitivity = asset_ctx.get("sensitivity_level") or "unavailable"
        asset_data_type = asset_ctx.get("data_type") or "unavailable"

        trust_score = user_ctx.get("trust_score")
        user_trust_score: Any = trust_score if trust_score is not None else "unavailable"

        incidents_any = incident_ctx.get("incidents")
        if incidents_any is None:
            incidents_any = incident_ctx.get("past_incidents")
        if isinstance(incidents_any, list):
            recent_incidents: Any = len(incidents_any)
        else:
            recent_incidents = "unavailable"

        return {
            "event_id": event.get("event_id"),
            "timestamp": event.get("timestamp"),
            "user_id": event.get("user_id"),
            "entity_id": event.get("entity_id"),
            "base_score": base_score,
            "risk_adjustment": validated_adjustment,
            "adjusted_risk_score": adjusted_risk,
            "risk_level": risk_level,
            "decision": decision,
            "recommended_action": self.risk_skill.recommend_action(
                risk_level, event.get("threat_classification", "")
            ),
            "base_score_analysis": contextual_analysis.get("base_score_analysis", ""),
            "risk_factors": contextual_analysis.get("risk_factors", []),
            "mitigating_factors": contextual_analysis.get("mitigating_factors", []),
            "adjustment_reasoning": contextual_analysis.get("adjustment_reasoning", ""),
            "decision_reasoning": contextual_analysis.get("decision_reasoning", ""),
            "context_summary": {
                "asset_sensitivity": asset_sensitivity,
                "asset_data_type": asset_data_type,
                "recent_incidents": recent_incidents,
                "triggered_rules_count": len(event.get("triggered_rules", [])),
            },
            "confidence": contextual_analysis.get("confidence", "medium"),
            "computation_method": "llm_react_contextual",
            "llm_driven": True,
            "execution_logs": list(getattr(self._local, "logs", [])),
        }

    def _parse_event_timestamp(self, ts: Any) -> datetime:
        if ts is None:
            return datetime.utcnow()
        s = str(ts).strip()
        if not s:
            return datetime.utcnow()
        s = s.replace("Z", "+00:00").replace(" ", "T")
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return datetime.utcnow()

    def _update_recent_incidents_cache(self, *, user_id: str, decision: str, event_ts: Any) -> None:
        if decision not in ("ESCALATE", "BLOCK"):
            return

        now = self._parse_event_timestamp(event_ts)
        cutoff = now - timedelta(days=30)

        key = make_cache_key("recent_incidents", user_id)
        payload = self.cache.get(key) if self.cache else None
        raw_ts: list[str] = []
        if isinstance(payload, dict) and isinstance(payload.get("timestamps"), list):
            raw_ts = [str(x) for x in payload.get("timestamps", [])]

        timestamps: list[str] = []
        seen: set[str] = set()
        for t in raw_ts:
            dt = self._parse_event_timestamp(t)
            iso = dt.isoformat(timespec="seconds")
            if iso not in seen:
                seen.add(iso)
                timestamps.append(iso)

        current_iso = now.isoformat(timespec="seconds")
        if current_iso not in seen:
            seen.add(current_iso)
            timestamps.append(current_iso)
        pruned: list[str] = []
        pruned_seen: set[str] = set()
        for t in timestamps:
            dt = self._parse_event_timestamp(t)
            if dt >= cutoff:
                iso = dt.isoformat(timespec="seconds")
                if iso not in pruned_seen:
                    pruned_seen.add(iso)
                    pruned.append(iso)

        if self.cache:
            self.cache.set(
                key,
                {"user_id": user_id, "timestamps": pruned, "window_days": 30},
                ttl=86400 * 120,
            )

    def _check_and_update_low_level_offenses(self, *, user_id: str, event_ts: Any, score: float) -> bool:
        now = self._parse_event_timestamp(event_ts)
        date_str = now.strftime("%Y-%m-%d")
        
        key = make_cache_key("low_offenders", f"{user_id}_{date_str}")
        payload = self.cache.get(key) if self.cache else None
        
        scores: list[float] = []
        if isinstance(payload, dict) and isinstance(payload.get("scores"), list):
            scores = payload.get("scores", [])
            
        is_penalty = len(scores) >= 3
        
        scores.append(score)
        
        if self.cache:
            self.cache.set(
                key,
                {"user_id": user_id, "date": date_str, "scores": scores},
                ttl=86400 * 2,
            )
            
        return is_penalty

    def clear_caches(self) -> None:
        """Clear the SQLite cache."""
        if self.cache:
            self.cache.clear()
        self._data_signature = None

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self.cache:
            return self.cache.get_stats()
        return {"cache_type": "disabled"}

    def _compute_data_signature(self) -> Optional[Tuple[float, ...]]:
        if self._data_dir is None:
            return None
        files = [self._data_dir / "policy_db.json"]
        sig: list[float] = []
        for p in files:
            try:
                sig.append(p.stat().st_mtime)
            except Exception:
                sig.append(-1.0)
        return tuple(sig)

    def _invalidate_caches_if_data_changed(self) -> None:
        if not self.enable_caching:
            return
        sig = self._compute_data_signature()
        if sig is None:
            return
        if self._data_signature is None:
            self._data_signature = sig
            return
        if sig != self._data_signature:
            self._print("[Cache] Data files changed, invalidating caches")
            self.clear_caches()
            self._data_signature = sig

    def _make_llm_cache_key(self, *, event: Dict[str, Any], context: Dict[str, Any], language: str) -> str:
        payload = {
            "language": language,
            "event": {
                "event_id": event.get("event_id"),
                "combined_score": event.get("combined_score"),
                "confidence": event.get("confidence"),
                "cold_start": event.get("cold_start"),
                "threat_classification": event.get("threat_classification"),
                "dimension_scores": event.get("dimension_scores"),
                "triggered_rules": event.get("triggered_rules"),
                "user_id": event.get("user_id"),
                "entity_id": event.get("entity_id"),
            },
            "context_summary": {
                "asset": context.get("asset"),
                "user": context.get("user"),
                "policy_thresholds": context.get("policy_thresholds"),
                "incident_history": context.get("incident_history"),
                "rule_explanations": context.get("rule_explanations"),
                "cert_identity": context.get("cert_identity"),
                "cert_telemetry": context.get("cert_telemetry"),
                "cert_baseline": context.get("cert_baseline"),
                "cert_deviations": context.get("cert_deviations"),
            },
            "prompt_version": 2,
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _analyze_contextual_risk_cached(
        self, *, event: Dict[str, Any], context: Dict[str, Any], language: str,
    ) -> Dict[str, Any]:
        if not (self.enable_caching and self.enable_llm_cache and self.cache):
            self._last_llm_cache_hit = False
            return self.llm.analyze_contextual_risk(event=event, context=context, language=language)

        cache_key = self._make_llm_cache_key(event=event, context=context, language=language)
        cache_key_full = make_cache_key("llm_analysis", cache_key)

        cached = self.cache.get(cache_key_full)
        if cached is not None:
            self._last_llm_cache_hit = True
            return cached

        self._last_llm_cache_hit = False
        result = self.llm.analyze_contextual_risk(event=event, context=context, language=language)

        if isinstance(result, dict) and "risk_adjustment" in result:
            self.cache.set(cache_key_full, result)

        return result

    def _react_gather_context(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Gather context for the LLM via MCP tool calls."""
        context: Dict[str, Any] = {}
        self._last_tool_cache_hits = 0
        self._invalidate_caches_if_data_changed()

        # Asset context
        if event.get("entity_id"):
            entity_id = str(event.get("entity_id"))
            try:
                meta = self._call_tool("cert.telemetry.get_file_metadata", {"file_id": entity_id})
                if isinstance(meta, dict) and meta.get("available"):
                    created_by = meta.get("created_by") or meta.get("user_id")
                    created_at = meta.get("created_at") or meta.get("last_seen")
                    context["asset"] = {
                        "sensitivity_level": meta.get("sensitivity_level"),
                        "data_type": meta.get("data_type"),
                        "filename": meta.get("filename"),
                        "created_by": created_by,
                        "created_at": created_at,
                        "entity_id": meta.get("entity_id"),
                        "sources": meta.get("sources"),
                    }
            except Exception as e:
                context["asset"] = {"available": False, "reason": f"{type(e).__name__}: {e}"}

        # CERT: Identity + telemetry
        user_id = event.get("user_id")
        event_ts = event.get("timestamp")
        if user_id and event_ts:
            try:
                context["cert_identity"] = self._call_tool(
                    "cert.identity.get_user_context",
                    {"user_id": str(user_id), "timestamp": str(event_ts)},
                )
            except Exception as e:
                context["cert_identity"] = {"available": False, "reason": f"{type(e).__name__}: {e}"}

            try:
                baseline = self._call_tool(
                    "cert.telemetry.get_user_baseline",
                    {"user_id": str(user_id), "as_of_ts": str(event_ts), "lookback_days": 30},
                )
                context["cert_baseline"] = baseline

                t = datetime.fromisoformat(str(event_ts).replace("Z", "+00:00").replace(" ", "T"))
                start = t - timedelta(days=1)
                start_s = start.isoformat(timespec="seconds")
                end_s = t.isoformat(timespec="seconds")

                context["cert_telemetry"] = self._call_tool(
                    "cert.telemetry.get_user_summary",
                    {"user_id": str(user_id), "start_ts": start_s, "end_ts": end_s},
                )
                context["cert_deviations"] = self._call_tool(
                    "cert.telemetry.get_deviations",
                    {"user_id": str(user_id), "start_ts": start_s, "end_ts": end_s, "baseline": baseline},
                )
            except Exception as e:
                context.setdefault("cert_telemetry", {"available": False, "reason": f"{type(e).__name__}: {e}"})
                context.setdefault("cert_baseline", {"available": False, "reason": f"{type(e).__name__}: {e}"})
                context.setdefault("cert_deviations", {"available": False, "reason": f"{type(e).__name__}: {e}"})

        # Policy thresholds
        context["policy_thresholds"] = self._call_tool("local_policy.get_thresholds", {})

        # Recent incidents
        if not event.get("cold_start") and user_id and self.enable_caching and self.cache:
            key = make_cache_key("recent_incidents", str(user_id))
            payload = self.cache.get(key) or {}
            timestamps = payload.get("timestamps") if isinstance(payload, dict) else None
            current_dt = self._parse_event_timestamp(event_ts)
            filtered: list[str] = []
            seen: set[str] = set()
            if isinstance(timestamps, list):
                for t in timestamps:
                    dt = self._parse_event_timestamp(t)
                    if dt == current_dt:
                        continue
                    iso = dt.isoformat(timespec="seconds")
                    if iso not in seen:
                        seen.add(iso)
                        filtered.append(iso)
            context["incident_history"] = {
                "available": True,
                "source": "decision_agent_cache",
                "user_id": str(user_id),
                "incidents": filtered,
            }

        # Rule explanations
        triggered_rules = event.get("triggered_rules", [])
        if triggered_rules:
            context["rule_explanations"] = self._call_tool(
                "cert.rule_library.explain",
                {"rule_ids": list(triggered_rules[:10])},
            )

        return context

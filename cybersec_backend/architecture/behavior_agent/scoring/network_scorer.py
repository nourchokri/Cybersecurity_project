"""
Rule-based verification layer on top of the ML model.
The model detects anomalies. The scorer confirms whether
the traffic pattern actually matches known attack behavior.

Verdict:
  "confirmed"  — model + rules agree, keep the flag
  "downgraded" — model flagged but rules are weak, lower score
  "rejected"   — model flagged but traffic looks normal, clear flag
"""

ATTACK_PORTS = {
    53:   "dns_amplification",
    123:  "ntp_amplification",
    161:  "snmp_amplification",
    389:  "ldap_amplification",
    1433: "mssql_flood",
    1900: "ssdp_amplification",
    137:  "netbios_amplification",
    111:  "portmap_amplification",
    69:   "tftp_amplification",
}

# Ports that are almost always legitimate
BENIGN_PORTS = {80, 443, 8080, 8443, 22, 25, 587, 993, 995}


def verify(prediction: dict, events: list) -> dict:
    """
    Input:
        prediction: output from network_model.predict()
        events:     list of Team 1 network_connection event dicts

    Output: dict with verdict, final_score, final_flagged, scorer_rules
    """
    if not events:
        return _result("rejected", 0.0, False, ["no_events"])

    meta      = events[0].get("metadata", {})
    dst_port  = int(meta.get("dst_port", 0) or 0)
    protocol  = str(meta.get("protocol", "tcp") or "tcp").upper()
    bytes_sent = float(meta.get("bytes_sent", 0) or 0)
    bytes_recv = float(meta.get("bytes_received", 0) or 0)
    model_score = prediction.get("combined_score", 0)
    model_flagged = prediction.get("flagged", False)

    # If model didn't flag — trust it, return clean
    if not model_flagged:
        return _result("clean", model_score, False, ["model_score_below_threshold"])

    # ── Scoring signals ───────────────────────────────────────────
    signals      = []
    signal_score = 0.0

    # Signal 1: Amplification ratio
    if bytes_sent > 0:
        ratio = bytes_recv / bytes_sent
        if ratio > 50:
            signals.append(f"amplification_ratio_critical_{int(ratio)}x")
            signal_score += 0.5
        elif ratio > 10:
            signals.append(f"amplification_ratio_high_{int(ratio)}x")
            signal_score += 0.3
        elif ratio > 3:
            signals.append(f"amplification_ratio_medium_{int(ratio)}x")
            signal_score += 0.1
    elif bytes_recv == 0 and protocol == "TCP":
        # SYN flood: sent packets with no response
        signals.append("syn_no_response")
        signal_score += 0.4

    # Signal 2: Known attack port
    if dst_port in ATTACK_PORTS:
        signals.append(f"attack_port_{dst_port}_{ATTACK_PORTS[dst_port]}")
        signal_score += 0.4

    # Signal 3: Protocol matches port
    if dst_port == 53 and protocol == "UDP":
        signals.append("dns_udp_match")
        signal_score += 0.2
    if dst_port in {123, 161, 1900, 111} and protocol == "UDP":
        signals.append("udp_amplification_protocol_match")
        signal_score += 0.2

    # Signal 4: High UDP receive volume
    if protocol == "UDP" and bytes_recv > 100_000:
        signals.append("udp_high_receive_volume")
        signal_score += 0.2

    # ── Counter-signals (evidence this is benign) ─────────────────
    counter_score = 0.0

    # Normal HTTPS/HTTP traffic
    if dst_port in BENIGN_PORTS and protocol == "TCP":
        counter_score += 0.4
        signals.append(f"benign_port_{dst_port}")

    # Reasonable ratio (normal web traffic is 1x-4x)
    if bytes_sent > 0 and (bytes_recv / bytes_sent) < 5 and dst_port in BENIGN_PORTS:
        counter_score += 0.3
        signals.append("normal_byte_ratio")

    # Both bytes present = established connection (not a flood)
    if bytes_sent > 100 and bytes_recv > 100:
        counter_score += 0.1
        signals.append("bidirectional_traffic")

    # ── Final verdict ─────────────────────────────────────────────
    net_signal = signal_score - counter_score

    if net_signal >= 0.5:
        # Strong attack signals, weak counter-signals → confirm
        final_score = min(model_score * 1.0, 1.0)
        return _result("confirmed", round(final_score, 4), True, signals)

    elif net_signal >= 0.1:
        # Some attack signals but not conclusive → downgrade
        final_score = model_score * 0.6
        flagged     = final_score >= 0.40
        verdict     = "downgraded_confirmed" if flagged else "downgraded_rejected"
        return _result(verdict, round(final_score, 4), flagged, signals)

    else:
        # Counter-signals dominate → reject the model's flag
        return _result("rejected", round(model_score * 0.2, 4), False, signals)


def _result(verdict, score, flagged, signals):
    return {
        "verdict":       verdict,
        "final_score":   score,
        "final_flagged": flagged,
        "scorer_rules":  signals,
    }
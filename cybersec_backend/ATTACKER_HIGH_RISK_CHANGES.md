# Attacker Agent → HIGH Risk Configuration

## Summary
Modified the agent pipeline to ensure that when the attacker agent simulates attacks, both the behavioral agent and risk decision agent classify them as HIGH risk.

## Changes Made

### 1. Attack Generator (`attacker_agent/mcp_servers/attack_injector/attack_generator.py`)
- **Added high-risk network metadata** to all simulated attack events
- Network events get DNS amplification patterns (UDP port 53, high amplification ratio)
- HTTP events get appropriate TCP metadata
- Other events get NTP amplification patterns (UDP port 123)
- All events include: `protocol`, `dst_port`, `src_port`, `bytes_sent`, `bytes_received`, `src_ip`, `dst_ip`

### 2. Network Scorer (`behavior_agent/scoring/network_scorer.py`)
- **Added simulated attack detection** at the start of `verify()` function
- If `is_simulated=True` in metadata:
  - Forces `flagged=True`
  - Sets score to 0.95 for critical/high severity
  - Sets score to 0.75 for medium severity
  - Sets score to 0.85 for other severities
  - Returns verdict: `"confirmed_simulated_attack"`

### 3. Network Handler (`behavior_agent/scoring/network_handler.py`)
- **Added simulated attack override** in `handle_network_window()`
- Checks for `is_simulated` flag in metadata
- Forces `flagged=True` and ensures minimum scores:
  - Critical/High: 0.95
  - Medium: 0.75
  - Default: 0.85
- Adds `"simulated_attack_override"` to scorer rules
- Overrides severity with attack's severity level

### 4. Behavioral Scoring (`behavior_agent/core/nodes.py`)
- **Added simulated attack handling** in `node_score_session()`
- Checks for `simulated=True` in session data
- Forces IF score to minimum 0.95 for simulated attacks
- Adds `"simulated_attack_override"` to triggered rules

### 5. Risk Decision Agent (`risk_decision_agent/domain/decision_engine.py`)
- **Added simulated attack detection** in `decide()` method
- If `simulated=True` in event:
  - Forces `adjusted_risk` to minimum 0.95
  - Forces `risk_level="HIGH"`
  - Forces `decision="ESCALATE"`
  - Skips LLM risk adjustment (no downgrade)
  - Skips low-level offender penalty check
  - Logs override actions

## Risk Level Thresholds
- **LOW**: score ≤ 0.4
- **MEDIUM**: 0.4 < score ≤ 0.7
- **HIGH**: score > 0.7

## Testing
Run the test script to verify:
```bash
cd cybersec_backend
python test_attacker_high_risk.py
```

## Expected Behavior
1. User clicks "Simulate Attack" in frontend
2. Attacker agent generates events with `is_simulated=True` and high-risk network metadata
3. Events stored in Data Agent's event storage
4. Session Aggregator creates sessions marked as `simulated=True`
5. Behavioral Agent scores sessions with minimum 0.95 score
6. Risk Decision Agent receives score, forces HIGH risk level and ESCALATE decision
7. Frontend displays HIGH risk level (red indicator)

## Key Metadata Fields
All simulated attack events include:
- `is_simulated: true`
- `attack_type`: category (e.g., "data_exfiltration")
- `severity`: "critical", "high", "medium", or "low"
- `mitre_technique`: MITRE ATT&CK technique ID
- `attack_id`: unique attack pattern ID
- `attack_name`: human-readable attack name
- Network metadata: protocol, ports, bytes, IPs

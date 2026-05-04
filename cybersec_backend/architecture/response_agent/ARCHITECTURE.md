# Response Agent Architecture

## System Overview

The Response Agent implements a **hybrid decision-making system** that combines:
1. Rule-based reasoning (via LLM feature weighting)
2. Contextual analysis (via LLM direct decision)
3. Learned behavior (via Reinforcement Learning)

All three approaches are synthesized by an LLM orchestrator to produce the final decision.

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         RISK AGENT OUTPUT                           │
│  {                                                                  │
│    event_id, user_id, risk_level, adjusted_risk_score,             │
│    risk_factors[], mitigating_factors[], context_summary           │
│  }                                                                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RESPONSE ORCHESTRATION SERVICE                   │
│                                                                     │
│  Step 1: Parse Input                                               │
│  ├─ RiskAgentOutput.from_dict(risk_data)                           │
│  └─ Validate and structure data                                    │
│                                                                     │
│  Step 2: Parallel Decision Making (ThreadPoolExecutor)             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                             │   │
│  │  ┌──────────────────────┐  ┌──────────────────────┐       │   │
│  │  │ LLM Feature Weighter │  │ LLM Direct Decision  │       │   │
│  │  ├──────────────────────┤  ├──────────────────────┤       │   │
│  │  │ 1. Ask LLM for       │  │ 1. Send full context │       │   │
│  │  │    feature weights   │  │    to LLM            │       │   │
│  │  │ 2. Calculate         │  │ 2. LLM analyzes and  │       │   │
│  │  │    weighted score    │  │    recommends action │       │   │
│  │  │ 3. Map to action     │  │ 3. Return decision   │       │   │
│  │  └──────────┬───────────┘  └──────────┬───────────┘       │   │
│  │             │                          │                   │   │
│  │             │      ┌──────────────────────┐                │   │
│  │             │      │ RL Decision Maker    │                │   │
│  │             │      ├──────────────────────┤                │   │
│  │             │      │ 1. Extract features  │                │   │
│  │             │      │ 2. Discretize state  │                │   │
│  │             │      │ 3. Q-table lookup    │                │   │
│  │             │      │ 4. Select action     │                │   │
│  │             │      └──────────┬───────────┘                │   │
│  │             │                 │                            │   │
│  │             └─────────────────┼────────────────────────────┘   │
│  │                               │                                │
│  │                               ▼                                │
│  │                    DecisionOutput × 3                          │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Step 3: LLM Orchestrator                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                             │   │
│  │  Input: All 3 decisions + original risk data               │   │
│  │                                                             │   │
│  │  LLM Prompt:                                                │   │
│  │  "You are a decision orchestrator. Three AI systems        │   │
│  │   analyzed this event:                                     │   │
│  │   - LLM Weighted: ALLOW (conf: 0.25)                       │   │
│  │   - LLM Direct: MONITOR (conf: 0.65)                       │   │
│  │   - RL Model: ALLOW (conf: 0.72)                           │   │
│  │                                                             │   │
│  │   Make the FINAL decision considering:                     │   │
│  │   1. Agreement level                                       │   │
│  │   2. Confidence levels                                     │   │
│  │   3. Risk level                                            │   │
│  │   4. Historical learning (RL)"                             │   │
│  │                                                             │   │
│  │  Output: (final_action, confidence, reasoning)             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Step 4: Generate Explanations                                     │
│  ├─ Risk Explanation: Why is this HIGH/MEDIUM/LOW risk?            │
│  └─ Action Explanation: Why was this action chosen?                │
│                                                                     │
│  Step 5: Create FinalDecision Object                               │
│  └─ Combine all outputs into structured response                   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        ACTION EXECUTOR                              │
│                                                                     │
│  Risk Level Check:                                                 │
│  ├─ HIGH   → Auto-execute action                                   │
│  ├─ MEDIUM → Call user via Twilio                                  │
│  └─ LOW    → Log only                                              │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   HIGH RISK  │  │ MEDIUM RISK  │  │   LOW RISK   │             │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤             │
│  │ BLOCK user   │  │ Twilio call  │  │ Log event    │             │
│  │ Lock account │  │ "Press 1 to  │  │ No action    │             │
│  │ Alert SIEM   │  │  approve"    │  │ needed       │             │
│  │ Notify team  │  │ Wait for     │  │              │             │
│  │              │  │ response     │  │              │             │
│  │ Status:      │  │              │  │ Status:      │             │
│  │ AUTO_EXECUTED│  │ Status:      │  │ LOGGED       │             │
│  │              │  │ PENDING_USER │  │              │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FINAL RESPONSE                              │
│  {                                                                  │
│    event_id, final_action, execution_status,                       │
│    llm_weighted_decision, llm_direct_decision, rl_decision,        │
│    orchestrator_reasoning, risk_explanation, action_explanation,   │
│    user_approval_required, twilio_call_sid                         │
│  }                                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. LLM Feature Weighter

**Purpose**: Assign importance weights to different features and calculate action.

**Process**:
1. Send risk data to LLM
2. LLM returns weights for:
   - base_score_weight
   - risk_factors_weight
   - mitigating_factors_weight
   - context_weight
   - confidence_weight
3. Calculate weighted score
4. Map score to action (ALLOW/MONITOR/ESCALATE/BLOCK)

**Example**:
```
Weights: {base: 0.7, risk_factors: 0.8, mitigating: 0.6, context: 0.5, confidence: 0.75}
Calculation: (0.13 * 0.7) + (2/10 * 0.8) - (1/10 * 0.6) + ... = 0.25
Action: ALLOW (score < 0.3)
```

### 2. LLM Direct Decision

**Purpose**: Make decision based on full contextual analysis.

**Process**:
1. Send complete risk data to LLM
2. LLM analyzes:
   - Risk factors
   - Mitigating factors
   - Context
   - User behavior
3. LLM directly recommends action
4. Returns action + confidence + reasoning

**Example**:
```
Input: "User MJS0890 accessed system from new device at 2 AM..."
Output: {
  action: "MONITOR",
  confidence: 0.65,
  reasoning: "While unusual, user is a technician who may work odd hours..."
}
```

### 3. RL Decision Maker

**Purpose**: Learn from past decisions and outcomes.

**Algorithm**: Q-Learning
- **State**: Discretized features (risk_score, risk_level, factor_counts)
- **Actions**: ALLOW, MONITOR, ESCALATE, BLOCK
- **Reward**: Based on outcome (SUCCESS: +1, FALSE_POSITIVE: -0.5, etc.)
- **Policy**: Epsilon-greedy (90% exploit, 10% explore)

**Process**:
1. Extract features from risk data
2. Discretize into state bins
3. Look up Q-values for state
4. Select best action (or explore)
5. Return action + confidence

**Q-Table Example**:
```
State: "8_2_3_1" (risk_bin=8, level=HIGH, rf=3, mf=1)
Q-values: {
  ALLOW: 0.12,
  MONITOR: 0.45,
  ESCALATE: 0.78,  ← Best action
  BLOCK: 0.65
}
```

**Training**:
```python
# User approves action
train(features, action="ESCALATE", reward=+1.0, outcome="SUCCESS")

# User denies action (false positive)
train(features, action="BLOCK", reward=-0.5, outcome="FALSE_POSITIVE")

# Security incident occurred
train(features, action="ALLOW", reward=-2.0, outcome="INCIDENT")
```

### 4. LLM Orchestrator

**Purpose**: Synthesize all three decisions into final choice.

**Process**:
1. Receive all 3 decisions
2. Analyze agreement/disagreement
3. Consider confidence levels
4. Factor in risk level
5. Make final decision
6. Generate reasoning

**Decision Logic**:
```
If all 3 agree → High confidence in that action
If 2/3 agree → Moderate confidence, explain dissent
If all disagree → Analyze which is most trustworthy:
  - High confidence LLM direct?
  - RL model with many training samples?
  - Risk level supports one action?
```

**Example**:
```
LLM Weighted: ALLOW (0.25)
LLM Direct: MONITOR (0.65)
RL Model: ALLOW (0.72)

Orchestrator: "Two systems recommend ALLOW with high confidence. 
The direct LLM suggests monitoring due to unusual device, but 
the RL model has learned from similar cases that this is typically 
legitimate. Final decision: ALLOW with increased logging."
```

### 5. Action Executor

**Purpose**: Execute the final decision based on risk level.

**Risk Level Routing**:

#### HIGH Risk → Auto-Execute
```python
if risk_level == "HIGH":
    if action == "BLOCK":
        firewall.block_user(user_id)
        account.lock(user_id)
        siem.create_incident(event)
    elif action == "ESCALATE":
        siem.create_high_priority_ticket(event)
        notify_security_team(event)
    return "AUTO_EXECUTED"
```

#### MEDIUM Risk → User Approval
```python
if risk_level == "MEDIUM":
    phone = get_user_phone(user_id)
    call_sid = twilio.call(
        to=phone,
        message="Security alert. Press 1 to approve, 2 to deny."
    )
    return "PENDING_USER", call_sid
```

#### LOW Risk → Log Only
```python
if risk_level == "LOW":
    logger.info(f"Low risk event: {event_id}")
    return "LOGGED"
```

## Reinforcement Learning Details

### State Representation

Features are discretized into bins:
```python
risk_score: 0.0-1.0 → bins 0-10
risk_level: LOW=0, MEDIUM=1, HIGH=2
risk_factors_count: 0-5+ (capped at 5)
mitigating_factors_count: 0-5+ (capped at 5)

State: "8_2_3_1"
       │ │ │ └─ 1 mitigating factor
       │ │ └─── 3 risk factors
       │ └───── HIGH risk (2)
       └─────── Risk score bin 8 (0.8-0.9)
```

### Q-Learning Update

```python
Q(s,a) ← Q(s,a) + α[r + γ max Q(s',a') - Q(s,a)]

Where:
- α = learning_rate (0.1)
- γ = discount_factor (0.95)
- r = reward
- s = current state
- a = action taken
- s' = next state
```

### Reward Structure

| Outcome | Reward | Description |
|---------|--------|-------------|
| SUCCESS | +1.0 | Correct decision, no incident |
| FALSE_POSITIVE | -0.5 | Blocked legitimate activity |
| FALSE_NEGATIVE | -1.0 | Allowed malicious activity |
| INCIDENT | -2.0 | Security incident occurred |

### Training Sources

1. **User Approval** (automatic):
   - User approves → SUCCESS (+1.0)
   - User denies → FALSE_POSITIVE (-0.5)

2. **Manual Feedback** (via API):
   - Security team reviews outcome
   - Provides feedback via `/api/v1/response/train/`

3. **Incident Correlation**:
   - If incident occurs within 24h of ALLOW decision
   - Automatically train with INCIDENT reward (-2.0)

## Twilio Integration

### Call Flow

```
1. MEDIUM risk detected
   ↓
2. Get user phone number
   ↓
3. Twilio.call(to=phone, url=callback_url)
   ↓
4. User answers
   ↓
5. TwiML: "Press 1 to approve, 2 to deny"
   ↓
6. User presses digit
   ↓
7. Twilio → /api/v1/response/twilio/gather/
   ↓
8. Parse digit (1=approve, 2=deny)
   ↓
9. Execute or deny action
   ↓
10. Train RL model with user feedback
```

### TwiML Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">
        This is a security alert from your cybersecurity system.
        Event ID: MJS0890_2026-04-23T05:32:31.
        User: MJS0890.
        Recommended action: ESCALATE.
        Press 1 to approve this action.
        Press 2 to deny this action.
    </Say>
    <Gather numDigits="1" action="/api/v1/response/twilio/gather" method="POST">
        <Say voice="alice">Please press 1 to approve, or 2 to deny.</Say>
    </Gather>
</Response>
```

## Performance Considerations

### Parallel Processing

Three decision methods run in parallel using `ThreadPoolExecutor`:
```python
with ThreadPoolExecutor(max_workers=3) as executor:
    future_weighted = executor.submit(llm_weighter.decide, risk_output)
    future_direct = executor.submit(llm_direct.decide, risk_output)
    future_rl = executor.submit(rl_decision_maker.decide, risk_output)
```

**Benefit**: Reduces total processing time from ~6s to ~2s

### LLM API Optimization

- **Temperature**: 0.3-0.5 for consistent decisions
- **Max Tokens**: 500-1500 based on task
- **Timeout**: 30s with retry logic
- **Caching**: Consider caching similar events

### RL Model Efficiency

- **Q-table**: In-memory dictionary (fast lookup)
- **State Space**: Discretized to ~1000 states (manageable)
- **Persistence**: Pickle file saved after each training
- **Cold Start**: Random initialization for unseen states

## Error Handling

### LLM Failures

```python
try:
    decision = llm.decide(risk_output)
except Exception as e:
    # Fallback to rule-based
    decision = fallback_decision(risk_output.risk_level)
```

### RL Model Failures

```python
try:
    action = rl_model.predict(features)
except Exception as e:
    # Fallback to risk level mapping
    action = {"LOW": "ALLOW", "MEDIUM": "MONITOR", "HIGH": "ESCALATE"}[risk_level]
```

### Twilio Failures

```python
try:
    call_sid = twilio.call(phone)
except Exception as e:
    # Fallback to SMS or email
    send_sms_notification(phone, message)
    # Or auto-deny for safety
    return "DENIED"
```

## Security Considerations

1. **Authentication**: All API endpoints should require authentication
2. **Rate Limiting**: Prevent abuse of training endpoint
3. **Input Validation**: Validate all risk data inputs
4. **Audit Logging**: Log all decisions and actions
5. **Twilio Security**: Validate webhook signatures
6. **RL Model Poisoning**: Monitor for adversarial training attempts

## Future Enhancements

1. **Deep RL**: Replace Q-Learning with DQN or PPO
2. **Ensemble Methods**: Add more decision models
3. **Explainable AI**: SHAP values for feature importance
4. **A/B Testing**: Compare decision strategies
5. **Real-time Dashboard**: Monitor decisions and RL performance
6. **Integration**: SIEM, firewall, IAM systems
7. **Multi-Agent**: Coordinate with other security agents

## Metrics & Monitoring

### Key Metrics

- **Decision Accuracy**: % of correct decisions
- **False Positive Rate**: % of blocked legitimate activity
- **False Negative Rate**: % of allowed malicious activity
- **Response Time**: Time from risk input to action execution
- **RL Model Performance**: Q-value convergence, training samples
- **User Approval Rate**: % of MEDIUM risk approvals

### Monitoring Endpoints

- `GET /api/v1/response/rl/stats/` - RL model statistics
- `GET /api/v1/response/metrics/` - Decision metrics (TODO)
- `GET /api/v1/response/audit/` - Audit log (TODO)

---

This architecture provides a robust, explainable, and adaptive decision-making system that learns from experience while maintaining human oversight for critical decisions.

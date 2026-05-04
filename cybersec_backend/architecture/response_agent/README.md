# Response Agent

## Overview

The Response Agent is the final decision-making layer in the cybersecurity pipeline. It takes the output from the Risk Decision Agent and makes a **hybrid decision** combining:

1. **LLM Feature Weighting** - LLM assigns weights to features and calculates action
2. **LLM Direct Decision** - LLM analyzes full context and suggests action
3. **RL Model Decision** - Reinforcement Learning model trained on past outcomes

An **LLM Orchestrator** then combines all three decisions to make the final call.

## Architecture

```
Risk Agent Output
    ↓
┌─────────────────────────────────────────┐
│  PARALLEL PROCESSING                    │
├─────────────────────────────────────────┤
│  1. LLM Feature Weighting               │
│  2. LLM Direct Decision                 │
│  3. RL Model Decision                   │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  LLM ORCHESTRATOR                       │
│  - Compares all 3 decisions             │
│  - Makes final decision                 │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  ACTION EXECUTION                       │
│  - HIGH: Auto-execute                   │
│  - MEDIUM: Call user (Twilio)           │
│  - LOW: Log only                        │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  EXPLANATION                            │
│  - Why risk is high/medium/low          │
│  - Why this action was chosen           │
└─────────────────────────────────────────┘
```

## Features

### 1. Hybrid Decision Making
- **LLM Feature Weighting**: Assigns importance weights to different features
- **LLM Direct**: Makes decision based on full context analysis
- **RL Model**: Learns from past approve/deny outcomes

### 2. Risk-Based Action Execution
- **HIGH Risk**: Automatic execution (BLOCK/ESCALATE)
- **MEDIUM Risk**: Human-in-the-loop via Twilio call
- **LOW Risk**: Log only, no action needed

### 3. Reinforcement Learning
- Q-Learning agent that learns from feedback
- Trains on user approval/denial decisions
- Improves over time based on outcomes

### 4. Twilio Integration
- Voice calls for MEDIUM risk events
- User can approve (press 1) or deny (press 2)
- SMS notifications as alternative

### 5. Explainability
- LLM explains why risk is high/medium/low
- LLM explains why specific action was chosen
- Full reasoning chain from all decision components

## API Endpoints

### Main Processing
```
POST /api/v1/response/process/
```
Process risk agent output and return final decision.

**Request Body**: Risk agent output JSON

**Response**:
```json
{
  "event_id": "...",
  "final_action": "ALLOW|MONITOR|ESCALATE|BLOCK",
  "execution_status": "AUTO_EXECUTED|PENDING_USER|LOGGED",
  "llm_weighted_decision": {...},
  "llm_direct_decision": {...},
  "rl_decision": {...},
  "orchestrator_reasoning": "...",
  "risk_explanation": "...",
  "action_explanation": "...",
  "user_approval_required": false,
  "twilio_call_sid": null
}
```

### User Approval
```
POST /api/v1/response/approval/
```
Handle user approval/denial after Twilio interaction.

### RL Training
```
POST /api/v1/response/train/
```
Train RL model from feedback.

**Request Body**:
```json
{
  "event_id": "...",
  "risk_data": {...},
  "action_taken": "ALLOW|BLOCK|ESCALATE|MONITOR",
  "outcome": "SUCCESS|FALSE_POSITIVE|FALSE_NEGATIVE|INCIDENT"
}
```

### RL Statistics
```
GET /api/v1/response/rl/stats/
```
Get RL model statistics.

### Health Check
```
GET /api/v1/response/health/
```

## Configuration

### Environment Variables

Add to `cybersec_backend/.env`:

```bash
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1234567890
TEST_PHONE_NUMBER=+1234567890  # For testing

# Response Agent Configuration
RESPONSE_AGENT_CALLBACK_URL=http://localhost:8000/api/v1/response/twilio/callback
```

### Install Twilio (Optional)

```bash
pip install twilio
```

If Twilio is not installed or not configured, the agent will use a mock client for testing.

## Usage

### 1. Start Django Server

```bash
cd cybersec_backend
python manage.py runserver
```

### 2. Test the Agent

```bash
python test_response_agent.py
```

This will run a test suite covering:
- LOW risk events (log only)
- HIGH risk events (auto-execute)
- MEDIUM risk events (user approval)
- RL model training
- RL statistics

### 3. Integration with Risk Agent

The Risk Decision Agent should forward its output to the Response Agent:

```python
import requests

risk_output = {
    "event_id": "...",
    "risk_level": "HIGH",
    "adjusted_risk_score": 0.85,
    # ... other fields
}

response = requests.post(
    "http://localhost:8000/api/v1/response/process/",
    json=risk_output
)

final_decision = response.json()
print(f"Final action: {final_decision['final_action']}")
```

## RL Model Training

The RL model learns from feedback in two ways:

### 1. Automatic (User Approval)
When a user approves/denies a MEDIUM risk action, the model automatically trains:
- **Approved** → Positive reward (SUCCESS)
- **Denied** → Negative reward (FALSE_POSITIVE)

### 2. Manual (Outcome Feedback)
You can manually train the model with actual outcomes:

```python
import requests

training_data = {
    "event_id": "...",
    "risk_data": {...},
    "action_taken": "BLOCK",
    "outcome": "SUCCESS"  # or FALSE_POSITIVE, FALSE_NEGATIVE, INCIDENT
}

requests.post(
    "http://localhost:8000/api/v1/response/train/",
    json=training_data
)
```

**Reward Structure**:
- `SUCCESS`: +1.0 (correct decision)
- `FALSE_POSITIVE`: -0.5 (blocked legitimate activity)
- `FALSE_NEGATIVE`: -1.0 (allowed malicious activity)
- `INCIDENT`: -2.0 (security incident occurred)

## File Structure

```
response_agent/
├── api/
│   ├── views.py          # API endpoints
│   ├── urls.py           # URL routing
│   └── serializers.py    # Request/response serializers
├── application/
│   └── orchestration_service.py  # Main orchestrator
├── domain/
│   ├── models.py         # Data models
│   ├── llm_weighting.py  # LLM feature weighting
│   ├── llm_decision.py   # LLM direct decision
│   ├── rl_decision.py    # RL-based decision
│   └── llm_orchestrator.py  # Final LLM orchestrator
├── infrastructure/
│   ├── llm_client.py     # LLM API client
│   ├── twilio_client.py  # Twilio integration
│   └── rl_model.py       # RL model (Q-Learning)
└── skills/
    └── action_executor.py  # Execute actions
```

## Example Output

### LOW Risk Event
```
Final Action: ALLOW
Execution Status: LOGGED
Risk Explanation: "This event is considered LOW risk because the adjusted score (0.13) is well below the threshold, and there is a strong mitigating factor showing the activity is consistent with the user's role."
Action Explanation: "Activity is allowed to proceed normally with standard logging."
```

### HIGH Risk Event
```
Final Action: BLOCK
Execution Status: AUTO_EXECUTED
Risk Explanation: "This event is HIGH risk due to multiple failed login attempts from a suspicious IP at an unusual time (3 AM) while attempting to access sensitive data."
Action Explanation: "Activity is immediately blocked to prevent potential security incident. The user account has been locked and security team notified."
```

### MEDIUM Risk Event
```
Final Action: ESCALATE
Execution Status: PENDING_USER
User Approval Required: true
Twilio Call SID: CA1234567890abcdef
Risk Explanation: "This event is MEDIUM risk due to unusual behavior pattern and access to sensitive resources, but the user has legitimate access rights."
Action Explanation: "Activity requires human review before proceeding. A call has been placed to the security operator for approval."
```

## Future Enhancements

1. **Advanced RL Models**: Replace Q-Learning with Deep Q-Networks (DQN) or Policy Gradient methods
2. **Multi-Armed Bandits**: For exploration/exploitation tradeoff
3. **Integration with SIEM**: Send alerts to Splunk, ELK, etc.
4. **Firewall Integration**: Automatically block IPs/users
5. **Slack/Teams Integration**: Alternative to Twilio for notifications
6. **Dashboard**: Real-time monitoring of decisions and RL model performance
7. **A/B Testing**: Compare different decision strategies

## Troubleshooting

### LLM API Errors
- Check `LLM_API_KEY` and `LLM_BASE_URL` in `.env`
- Verify API is accessible: `curl https://tokenfactory.esprit.tn/api/health`

### Twilio Not Working
- Verify credentials in `.env`
- Check Twilio console for call logs
- Use mock client for testing: `use_mock_twilio=True`

### RL Model Not Learning
- Check training data: `GET /api/v1/response/rl/stats/`
- Ensure feedback is being provided
- Model file location: `cybersec_backend/data/rl_models/response_agent_rl.pkl`

## License

Part of the Cybersecurity Multi-Agent SOC Platform.

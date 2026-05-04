# Response Agent Integration Guide

## Quick Start

The Response Agent is now fully integrated into your cybersecurity platform. Here's how to use it:

## 1. Architecture Overview

```
┌─────────────────┐
│  Risk Agent     │ (Team 3)
│  Output         │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              RESPONSE AGENT (Team 4)                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ LLM Feature  │  │ LLM Direct   │  │ RL Model     │ │
│  │ Weighting    │  │ Decision     │  │ Decision     │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                 │                 │          │
│         └─────────────────┼─────────────────┘          │
│                           ▼                            │
│                  ┌─────────────────┐                   │
│                  │ LLM Orchestrator│                   │
│                  │ (Final Decision)│                   │
│                  └────────┬────────┘                   │
│                           │                            │
│                           ▼                            │
│                  ┌─────────────────┐                   │
│                  │ Action Executor │                   │
│                  └────────┬────────┘                   │
└──────────────────────────┼──────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
    ┌────────┐      ┌──────────┐      ┌─────────┐
    │  HIGH  │      │  MEDIUM  │      │   LOW   │
    │  Auto  │      │  Twilio  │      │   Log   │
    │ Execute│      │   Call   │      │   Only  │
    └────────┘      └──────────┘      └─────────┘
```

## 2. Integration with Risk Agent

### Option A: Automatic Forwarding (Recommended)

Update the Risk Decision Agent to automatically forward to Response Agent:

```python
# In risk_decision_agent/application/orchestration_service.py

from architecture.response_agent.application.orchestration_service import get_orchestration_service as get_response_service

def analyze_event(self, event_data):
    # ... existing risk analysis code ...
    
    # Forward to Response Agent
    try:
        response_service = get_response_service()
        final_decision = response_service.process_risk_decision(decision_result)
        logger.info(f"Response Agent decision: {final_decision}")
    except Exception as e:
        logger.error(f"Failed to forward to Response Agent: {e}")
    
    return decision_result
```

### Option B: Manual API Call

Call the Response Agent API from anywhere:

```python
import requests

risk_output = {
    "event_id": "MJS0890_2026-04-23T05:32:31.535756",
    "timestamp": "2026-04-23T05:32:31.535756",
    "user_id": "MJS0890",
    "entity_id": "",
    "base_score": 0.43,
    "risk_adjustment": -0.3,
    "adjusted_risk_score": 0.13,
    "risk_level": "LOW",
    "decision": "ALLOW",
    "recommended_action": "log event for audit trail",
    "risk_factors": [...],
    "mitigating_factors": [...],
    "context_summary": {...},
    "confidence": "medium",
    "computation_method": "llm_react_contextual",
    "llm_driven": True,
    "execution_logs": [...]
}

response = requests.post(
    "http://localhost:8000/api/v1/response/process/",
    json=risk_output
)

final_decision = response.json()
print(f"Final Action: {final_decision['final_action']}")
print(f"Execution Status: {final_decision['execution_status']}")
```

## 3. Testing

### Run Test Suite

```bash
cd cybersec_backend
python test_response_agent.py
```

This tests:
- ✅ Health check
- ✅ LOW risk event (log only)
- ✅ HIGH risk event (auto-execute)
- ✅ MEDIUM risk event (user approval)
- ✅ RL model training
- ✅ RL statistics

### Manual Testing

```bash
# Start Django server
python manage.py runserver

# In another terminal, test with curl
curl -X POST http://localhost:8000/api/v1/response/process/ \
  -H "Content-Type: application/json" \
  -d @test_risk_output.json
```

## 4. Configuration

### Required Settings

Add to `cybersec_backend/.env`:

```bash
# LLM Configuration (already exists)
LLM_API_KEY=sk-99f9c57b76a24384bb38d1380de94de6
LLM_BASE_URL=https://tokenfactory.esprit.tn/api
LLM_MODEL=hosted_vllm/Llama-3.1-70B-Instruct

# Twilio Configuration (for MEDIUM risk user approval)
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_FROM_NUMBER=+1234567890
TEST_PHONE_NUMBER=+1234567890

# Response Agent Configuration
RESPONSE_AGENT_CALLBACK_URL=http://localhost:8000/api/v1/response/twilio/callback
```

### Optional: Install Twilio

```bash
pip install twilio
```

**Note**: If Twilio is not configured, the agent will use a mock client (no real calls).

## 5. Understanding the Output

### Example Response

```json
{
  "event_id": "MJS0890_2026-04-23T05:32:31.535756",
  "user_id": "MJS0890",
  "timestamp": "2026-04-23T05:32:31.535756",
  "risk_level": "LOW",
  "final_action": "ALLOW",
  "execution_status": "LOGGED",
  
  "llm_weighted_decision": {
    "action": "ALLOW",
    "confidence": 0.25,
    "reasoning": "Weighted score: 0.25, below threshold",
    "source": "llm_weighted"
  },
  
  "llm_direct_decision": {
    "action": "MONITOR",
    "confidence": 0.65,
    "reasoning": "Activity is low risk but should be monitored",
    "source": "llm_direct"
  },
  
  "rl_decision": {
    "action": "ALLOW",
    "confidence": 0.72,
    "reasoning": "RL model predicts ALLOW based on past outcomes",
    "source": "rl_model"
  },
  
  "orchestrator_reasoning": "All three systems agree on allowing this activity. The LLM weighted approach and RL model both recommend ALLOW with high confidence. While the direct LLM suggests monitoring, the overall risk level is LOW and the activity is consistent with user behavior.",
  
  "confidence": 0.85,
  
  "risk_explanation": "This event is considered LOW risk because the adjusted score (0.13) is well below the threshold. While there are some risk factors like unusual device access, the mitigating factor of role consistency outweighs the concerns.",
  
  "action_explanation": "Activity is allowed to proceed normally with standard logging. No additional action is required as the risk level is LOW and all decision systems agree this is legitimate activity.",
  
  "user_approval_required": false,
  "user_approval_status": null,
  "twilio_call_sid": null
}
```

### Key Fields

- **final_action**: ALLOW | MONITOR | ESCALATE | BLOCK
- **execution_status**: 
  - `LOGGED` - LOW risk, just logged
  - `AUTO_EXECUTED` - HIGH risk, action executed automatically
  - `PENDING_USER` - MEDIUM risk, waiting for user approval
- **user_approval_required**: true if Twilio call was made
- **twilio_call_sid**: Twilio call ID for tracking

## 6. Risk Level Behavior

### LOW Risk
- **Action**: Log only
- **Execution**: Immediate
- **User Interaction**: None
- **Example**: Normal user activity, slight deviation from baseline

### MEDIUM Risk
- **Action**: Requires approval
- **Execution**: Pending user response
- **User Interaction**: Twilio voice call
  - Press 1 to approve
  - Press 2 to deny
- **Example**: Unusual but potentially legitimate activity

### HIGH Risk
- **Action**: Auto-execute (BLOCK/ESCALATE)
- **Execution**: Immediate
- **User Interaction**: None (post-incident notification)
- **Example**: Multiple failed logins, suspicious IP, data exfiltration attempt

## 7. RL Model Training

### Automatic Training (User Approval)

When a user approves/denies a MEDIUM risk action:
- **Approved** → Model learns this was correct (reward: +1.0)
- **Denied** → Model learns this was false positive (reward: -0.5)

### Manual Training (Outcome Feedback)

After an incident or investigation:

```python
import requests

training_data = {
    "event_id": "MJS0890_2026-04-23T05:32:31.535756",
    "risk_data": {...},  # Original risk agent output
    "action_taken": "BLOCK",
    "outcome": "SUCCESS"  # or FALSE_POSITIVE, FALSE_NEGATIVE, INCIDENT
}

requests.post(
    "http://localhost:8000/api/v1/response/train/",
    json=training_data
)
```

**Outcomes**:
- `SUCCESS`: Correct decision (+1.0 reward)
- `FALSE_POSITIVE`: Blocked legitimate activity (-0.5 reward)
- `FALSE_NEGATIVE`: Allowed malicious activity (-1.0 reward)
- `INCIDENT`: Security incident occurred (-2.0 reward)

### Check RL Model Stats

```bash
curl http://localhost:8000/api/v1/response/rl/stats/
```

Response:
```json
{
  "q_table_size": 42,
  "training_samples": 156,
  "actions": ["ALLOW", "MONITOR", "ESCALATE", "BLOCK"],
  "learning_rate": 0.1,
  "epsilon": 0.1
}
```

## 8. Twilio Integration (MEDIUM Risk)

### Setup Twilio

1. Sign up at https://www.twilio.com
2. Get your Account SID and Auth Token
3. Get a Twilio phone number
4. Add to `.env`:

```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1234567890
```

### Call Flow

1. MEDIUM risk event detected
2. Response Agent calls user via Twilio
3. User hears: "This is a security alert. Event ID: XXX. Press 1 to approve, 2 to deny."
4. User presses 1 or 2
5. Response Agent executes or denies action
6. RL model learns from user's decision

### Testing Without Twilio

Set `use_mock_twilio=True` in the service:

```python
service = get_orchestration_service(use_mock_twilio=True)
```

This will simulate calls without actually making them.

## 9. API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/response/health/` | GET | Health check |
| `/api/v1/response/process/` | POST | Process risk decision (main endpoint) |
| `/api/v1/response/approval/` | POST | Handle user approval |
| `/api/v1/response/train/` | POST | Train RL model |
| `/api/v1/response/rl/stats/` | GET | Get RL model statistics |
| `/api/v1/response/twilio/callback/` | POST | Twilio voice callback |
| `/api/v1/response/twilio/gather/` | POST | Twilio digit input |
| `/api/v1/response/twilio/status/` | POST | Twilio call status |

## 10. Monitoring & Debugging

### Check Logs

```bash
# Django logs
tail -f cybersec_backend/logs/django.log

# Response Agent specific logs
grep "Response" cybersec_backend/logs/django.log
```

### Debug Mode

Enable detailed logging in Django settings:

```python
LOGGING = {
    'loggers': {
        'architecture.response_agent': {
            'level': 'DEBUG',
        },
    },
}
```

### Common Issues

**Issue**: LLM API timeout
- **Solution**: Increase timeout in `llm_client.py` or check API status

**Issue**: RL model not found
- **Solution**: Model is created automatically on first use. Check `cybersec_backend/data/rl_models/`

**Issue**: Twilio calls not working
- **Solution**: Verify credentials, check Twilio console, or use mock client

## 11. Next Steps

1. **Test the agent** with your existing risk outputs
2. **Configure Twilio** for MEDIUM risk user approval
3. **Train the RL model** with historical data
4. **Monitor decisions** and adjust thresholds if needed
5. **Integrate with SIEM** for incident tracking
6. **Build dashboard** for real-time monitoring

## 12. Support

For issues or questions:
- Check `cybersec_backend/architecture/response_agent/README.md`
- Review test script: `test_response_agent.py`
- Check logs in Django console

## Architecture Files

```
cybersec_backend/architecture/response_agent/
├── api/
│   ├── views.py          # API endpoints
│   ├── urls.py           # URL routing
│   └── serializers.py    # Request/response validation
├── application/
│   └── orchestration_service.py  # Main orchestrator
├── domain/
│   ├── models.py         # Data models
│   ├── llm_weighting.py  # LLM feature weighting
│   ├── llm_decision.py   # LLM direct decision
│   ├── rl_decision.py    # RL-based decision
│   └── llm_orchestrator.py  # Final orchestrator
├── infrastructure/
│   ├── llm_client.py     # LLM API client
│   ├── twilio_client.py  # Twilio integration
│   └── rl_model.py       # Q-Learning RL model
├── skills/
│   └── action_executor.py  # Execute actions
└── README.md             # Detailed documentation
```

---

**The Response Agent is ready to use!** 🚀

Start the Django server and run `python test_response_agent.py` to see it in action.

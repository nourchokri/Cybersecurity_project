# Response Agent - Quick Reference

## 🎯 What It Does

Takes **Risk Agent output** → Makes **hybrid decision** (LLM + RL) → **Executes action** based on risk level

## 🔄 Flow

```
Risk Agent Output
    ↓
┌─────────────────────────────────┐
│  3 Parallel Decisions:          │
│  1. LLM Feature Weighting       │
│  2. LLM Direct Decision         │
│  3. RL Model (learns from past) │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  LLM Orchestrator               │
│  (combines all 3)               │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  Action Execution:              │
│  • HIGH → Auto-execute          │
│  • MEDIUM → Call user (Twilio)  │
│  • LOW → Log only               │
└─────────────────────────────────┘
```

## 📡 Main Endpoint

```bash
POST /api/v1/response/process/
```

**Input**: Risk agent output JSON  
**Output**: Final decision with explanations

## 🚀 Quick Test

```bash
# 1. Start server
cd cybersec_backend
python manage.py runserver

# 2. Run tests
python test_response_agent.py
```

## 📝 Example Usage

```python
import requests

risk_output = {
    "event_id": "TEST_001",
    "risk_level": "MEDIUM",
    "adjusted_risk_score": 0.55,
    "risk_factors": ["Unusual access pattern"],
    "mitigating_factors": ["User has valid credentials"],
    # ... other fields
}

response = requests.post(
    "http://localhost:8000/api/v1/response/process/",
    json=risk_output
)

decision = response.json()
print(f"Action: {decision['final_action']}")
print(f"Status: {decision['execution_status']}")
print(f"Explanation: {decision['action_explanation']}")
```

## 🎚️ Risk Level Behavior

| Risk Level | Action | Execution | User Interaction |
|------------|--------|-----------|------------------|
| **LOW** | Log only | Immediate | None |
| **MEDIUM** | Requires approval | Pending | Twilio call |
| **HIGH** | Auto-execute | Immediate | None (notify after) |

## 🔧 Configuration

Add to `.env`:
```bash
# Twilio (optional)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_FROM_NUMBER=+1234567890
```

## 📊 Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/response/health/` | GET | Health check |
| `/api/v1/response/process/` | POST | **Main** - Process decision |
| `/api/v1/response/train/` | POST | Train RL model |
| `/api/v1/response/rl/stats/` | GET | RL statistics |

## 🧠 RL Training

### Automatic (User Approval)
- User approves → SUCCESS (+1.0 reward)
- User denies → FALSE_POSITIVE (-0.5 reward)

### Manual (API)
```python
requests.post('/api/v1/response/train/', json={
    "event_id": "...",
    "risk_data": {...},
    "action_taken": "BLOCK",
    "outcome": "SUCCESS"  # or FALSE_POSITIVE, FALSE_NEGATIVE, INCIDENT
})
```

## 📈 Output Structure

```json
{
  "final_action": "ALLOW|MONITOR|ESCALATE|BLOCK",
  "execution_status": "LOGGED|PENDING_USER|AUTO_EXECUTED",
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

## 🎓 Key Features

✅ **Hybrid Decision** - LLM + RL combined  
✅ **Risk-Based Execution** - Auto/approval/log  
✅ **Learns from Feedback** - RL improves over time  
✅ **Explainable** - Full reasoning provided  
✅ **Twilio Integration** - Voice calls for approval  
✅ **Parallel Processing** - Fast (3 decisions at once)  

## 📚 Documentation

- **README.md** - Full documentation
- **ARCHITECTURE.md** - Technical deep dive
- **RESPONSE_AGENT_INTEGRATION.md** - Integration guide
- **RESPONSE_AGENT_SUMMARY.md** - Implementation summary
- **test_response_agent.py** - Test suite

## 🐛 Troubleshooting

**LLM not responding?**
- Check `LLM_API_KEY` in `.env`
- Verify API is accessible

**RL model not learning?**
- Check `/api/v1/response/rl/stats/`
- Ensure training data is being sent

**Twilio not working?**
- Verify credentials in `.env`
- Use mock mode: `use_mock_twilio=True`

## 🎯 Next Steps

1. ✅ Test with `python test_response_agent.py`
2. ⚙️ Configure Twilio (optional)
3. 🔗 Integrate with Risk Agent
4. 📊 Monitor decisions
5. 🎓 Train RL model with historical data

---

**Ready to use!** See full docs in README.md

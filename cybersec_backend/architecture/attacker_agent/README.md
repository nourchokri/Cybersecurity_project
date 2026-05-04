# Attacker Agent

## Overview

The Attacker Agent is an LLM-powered intelligent attack simulation system that generates context-aware attack patterns for testing security detection capabilities.

## Features

- **LLM-Powered Decisions**: Uses Llama 3.1 70B to make intelligent attack decisions
- **Context-Aware**: Analyzes real system activity to generate realistic attacks
- **CERT r4.2 Patterns**: 30+ real insider threat patterns from CERT dataset
- **Automatic Storage**: Integrates with data_agent's event storage
- **REST API**: Full API for attack management

## Architecture

```
attacker_agent/
├── agents/
│   └── llm_adversarial_agent.py    # LLM-powered agent
├── api/
│   ├── views.py                    # REST API endpoints
│   ├── urls.py                     # URL routing
│   └── serializers.py              # Request validation
├── application/
│   └── attacker_service.py         # Business logic
├── infrastructure/
│   └── mcp_integration.py          # MCP client management
├── mcp_servers/
│   └── attack_injector/            # Attack generation MCP
└── data/
    └── attacks/                    # CERT r4.2 patterns
```

## API Endpoints

### Base URL: `/api/v1/attacker/`

#### 1. Health Check
```bash
GET /api/v1/attacker/health/
```

**Response:**
```json
{
  "status": "healthy",
  "agent": "attacker_agent",
  "version": "1.0.0",
  "capabilities": [
    "intelligent_attack_generation",
    "context_aware_simulation",
    "llm_powered_decisions",
    "cert_r42_patterns"
  ]
}
```

#### 2. List Attack Patterns
```bash
GET /api/v1/attacker/patterns/
GET /api/v1/attacker/patterns/?category=data_exfiltration
GET /api/v1/attacker/patterns/?severity=high
```

**Response:**
```json
{
  "ok": true,
  "patterns": [
    {
      "id": "cert_r42_s1_aam0658",
      "name": "USB Exfiltration - Financial Documents",
      "category": "data_exfiltration",
      "mitre_technique": "T1052.001",
      "severity": "high",
      "description": "Employee copies sensitive files to USB"
    }
  ],
  "count": 1
}
```

#### 3. Inject Single Attack
```bash
POST /api/v1/attacker/inject/
Content-Type: application/json

{
  "attack_id": "cert_r42_s1_aam0658",
  "user_id": "alice",
  "device_id": "PC-001"
}
```

**Response:**
```json
{
  "ok": true,
  "attack_id": "cert_r42_s1_aam0658",
  "events_generated": 3,
  "events_stored": 3,
  "attack_name": "USB Exfiltration",
  "mitre_technique": "T1052.001",
  "severity": "high",
  "timestamp": "2026-05-01T14:30:00Z"
}
```

#### 4. Start Continuous Agent
```bash
POST /api/v1/attacker/start/
Content-Type: application/json

{
  "interval_seconds": 600,
  "max_attacks": 50
}
```

**Response:**
```json
{
  "ok": true,
  "message": "Adversarial agent started",
  "interval_seconds": 600,
  "max_attacks": 50,
  "timestamp": "2026-05-01T14:30:00Z"
}
```

#### 5. Stop Agent
```bash
POST /api/v1/attacker/stop/
```

**Response:**
```json
{
  "ok": true,
  "message": "Adversarial agent stopped",
  "timestamp": "2026-05-01T14:35:00Z"
}
```

#### 6. Get Statistics
```bash
GET /api/v1/attacker/stats/
```

**Response:**
```json
{
  "ok": true,
  "total_attacks": 15,
  "by_type": {
    "data_exfiltration": 5,
    "credential_theft": 3,
    "sabotage": 2
  },
  "by_severity": {
    "high": 8,
    "medium": 5,
    "low": 2
  },
  "agent_running": false,
  "timestamp": "2026-05-01T14:30:00Z"
}
```

#### 7. Get Attack History
```bash
GET /api/v1/attacker/history/?limit=50
```

**Response:**
```json
{
  "ok": true,
  "attacks": [
    {
      "attack_id": "cert_r42_s1_aam0658",
      "attack_name": "USB Exfiltration",
      "attack_type": "data_exfiltration",
      "mitre_technique": "T1052.001",
      "severity": "high",
      "timestamp": "2026-05-01T14:00:00Z",
      "user_id": "alice",
      "device_id": "PC-001",
      "event_count": 3
    }
  ],
  "count": 1,
  "limit": 50
}
```

## Integration with Data Agent

The attacker agent uses data_agent's event storage for storing attack events:

```python
# In attacker_service.py
from architecture.data_agent.infrastructure.mcp_integration import MCPClientManager

# Store events in data_agent's storage
self.data_agent_mcp = MCPClientManager()
self.data_agent_mcp.call_event_storage('store_events', {'events': events})
```

**All attack events have `is_simulated=True`** to distinguish them from real events.

## MCP Servers

### attack_injector
**Location:** `mcp_servers/attack_injector/`

**Tools:**
- `list_attack_patterns` - List available patterns
- `inject_attack` - Generate attack events
- `add_attack_pattern` - Add custom patterns

**Configuration:** See `mcp_config.json`

## LLM Agent

The adversarial agent uses the ReAct (Reason-Act-Observe) loop:

1. **OBSERVE**: Get current attack state and system context
2. **REASON**: LLM decides which attack to inject
3. **ACT**: Execute attack injection via MCP
4. **OBSERVE**: Feed results back to LLM
5. **REPEAT**: Continue loop

## Testing

### Test Health Endpoint
```bash
curl http://localhost:8000/api/v1/attacker/health/
```

### Test Attack Injection
```bash
curl -X POST http://localhost:8000/api/v1/attacker/inject/ \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "cert_r42_s1_aam0658",
    "user_id": "alice",
    "device_id": "PC-001"
  }'
```

### Verify Events Stored
```bash
# Query data_agent's storage for simulated events
curl -X POST http://localhost:8000/api/v1/data/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {"is_simulated": true},
    "limit": 10
  }'
```

## Configuration

### Environment Variables
```bash
# LLM Configuration (shared with data_agent)
ESPRIT_API_KEY=your_api_key
ESPRIT_BASE_URL=https://tokenfactory.esprit.tn/api
ESPRIT_MODEL=hosted_vllm/Llama-3.1-70B-Instruct

# Agent Configuration
ATTACKER_INTERVAL_SECONDS=600  # Attack every 10 minutes
ATTACKER_MAX_ATTACKS=100       # Stop after 100 attacks
```

### MCP Configuration
See `mcp_config.json` for MCP server settings.

## Development

### Adding New Attack Patterns
Add patterns to `data/attacks/attack_patterns.json`:

```json
{
  "id": "custom_attack_001",
  "name": "Custom Attack",
  "category": "data_exfiltration",
  "mitre_technique": "T1041",
  "severity": "high",
  "description": "Custom attack description",
  "sequence": [...]
}
```

### Extending the API
Add new endpoints in `api/views.py` and register in `api/urls.py`.

## Troubleshooting

### MCP Connection Errors
- Check `mcp_config.json` configuration
- Verify Python path is correct
- Check logs in `logs/attacker_agent.log`

### Attack Injection Fails
- Verify attack_id exists (use `/patterns/` endpoint)
- Check data_agent's event storage is running
- Review error logs

### Agent Won't Start
- Check if already running (use `/stats/` endpoint)
- Verify LLM API key is set
- Check MCP server connections

## Related Documentation

- [Data Agent README](../data_agent/README.md)
- [Integration Guide](../../../INTEGRATION_COMPLETE_SUMMARY.md)
- [MCP Architecture](../../../MCP_SERVERS_LOCATION.md)

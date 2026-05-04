# Data Agent - Django Integration

This Django app wraps your existing MCP servers and LLM agent into a REST API that integrates with the team's Django backend.

## Structure

```
data_agent/
├── api/                    # REST API layer
│   ├── views.py           # DRF views
│   ├── serializers.py     # Request/response serializers
│   └── urls.py            # URL routing
├── application/           # Business logic
│   └── data_service.py    # Orchestration service
├── infrastructure/        # External integrations
│   └── mcp_integration.py # MCP client manager
├── apps.py               # Django app config
└── README.md             # This file
```

## Installation

1. **Copy this folder** to their Django project:
   ```
   cp -r django_integration/data_agent/ /path/to/cybersec_backend/architecture/
   ```

2. **Update their `config/urls.py`** to add your agent:
   ```python
   path("api/v1/data/", include("architecture.data_agent.api.urls")),
   ```

3. **Update the API root view** in `config/urls.py` to include data_agent endpoints:
   ```python
   "data_agent": {
       "base_url": "/api/v1/data/",
       "endpoints": {
           "health": "GET /api/v1/data/health/",
           "collect": "POST /api/v1/data/collect/",
           "query": "POST /api/v1/data/query/",
           "analyze": "POST /api/v1/data/analyze/",
           "inject_attack": "POST /api/v1/data/inject-attack/",
           "stats": "GET /api/v1/data/stats/",
       }
   }
   ```

4. **Copy your core modules** to their project:
   ```
   cp -r agents/ /path/to/cybersec_backend/
   cp -r mcp_servers/ /path/to/cybersec_backend/
   cp -r collectors/ /path/to/cybersec_backend/
   cp -r data/ /path/to/cybersec_backend/
   ```

5. **Merge requirements**:
   Add your dependencies to their `requirements.txt`

6. **Configure environment**:
   Add your `.env` variables to their `.env` file

## API Endpoints

### Health Check
```bash
GET /api/v1/data/health/
```

### Collect Events
```bash
POST /api/v1/data/collect/
{
  "collectors": ["file", "network"]  # optional, empty = all
}
```

### Query Events
```bash
POST /api/v1/data/query/
{
  "start_date": "2026-04-01",
  "end_date": "2026-04-26",
  "event_type": "file_access",
  "user_id": "user123",
  "limit": 100
}
```

### Analyze Events
```bash
POST /api/v1/data/analyze/
{
  "query": "Find suspicious file access patterns",
  "start_date": "2026-04-01",
  "max_events": 100
}
```

### Inject Attack
```bash
POST /api/v1/data/inject-attack/
{
  "attack_type": "data_exfiltration",
  "count": 5
}
```

### Get Statistics
```bash
GET /api/v1/data/stats/
```

## Integration with Other Agents

Your data agent can forward suspicious events to other agents:

```python
# In your views.py, add forwarding logic similar to behavior_agent
def _forward_to_risk_agent(event_data: dict):
    import httpx
    team3_url = 'http://127.0.0.1:8000/api/v1/risk-decision/analyze/'
    with httpx.Client(timeout=90.0) as client:
        resp = client.post(team3_url, json=event_data)
```

## Testing

```bash
# Health check
curl http://localhost:8000/api/v1/data/health/

# Collect events
curl -X POST http://localhost:8000/api/v1/data/collect/ \
  -H "Content-Type: application/json" \
  -d '{"collectors": ["file"]}'

# Query events
curl -X POST http://localhost:8000/api/v1/data/query/ \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'
```

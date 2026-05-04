# Cybersecurity Multi-Agent SOC Platform

A Django-based backend for a multi-agent Security Operations Center (SOC) pipeline. Built with Django REST Framework, this platform provides REST API endpoints for cybersecurity risk analysis and decision-making.

**Pipeline:** Team 1 (Data Collector) → Team 2 (Behavior/Pattern Agent) → **Team 3 (Risk & Decision Agent)** → Team 4 (Response Agent)

---

## Quick Start

```powershell
cd cybersec_backend

# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
#    Edit .env with your ESPRIT_API_KEY and SUPABASE_DB_URL

# 3. Run migrations (one-time)
python manage.py migrate

# 4. Start the server
python manage.py runserver 8000
```

Then visit: `http://127.0.0.1:8000/`

---

## General Folder Structure

```
project_classe/
├── .env                          # Root env (optional, kept for reference)
├── .venv/                        # Python virtual environment
├── README.md                     # This file
│
└── cybersec_backend/             # ← Django project root
    ├── manage.py                 # Django entry point
    ├── requirements.txt          # All Python dependencies
    ├── .env                      # Environment variables (API keys, DB URL)
    ├── .gitignore
    ├── db.sqlite3                # Django ORM database (auto-created)
    ├── test_api.py               # Smoke test script for all endpoints
    │
    ├── config/                   # Django configuration
    │   ├── settings/
    │   │   ├── __init__.py       # Defaults to dev settings
    │   │   ├── base.py           # Shared settings (apps, middleware, DRF)
    │   │   ├── dev.py            # Debug mode, open CORS, browsable API
    │   │   └── prod.py           # Production: restricted CORS, JSON only
    │   ├── urls.py               # Root URL router → agent APIs
    │   ├── wsgi.py
    │   └── asgi.py
    │
    ├── architecture/             # All agents live here
    │   ├── data_agent/           # Team 1 — Data Collector (stub)
    │   ├── behavior_agent/       # Team 2 — Pattern Agent (stub)
    │   ├── risk_decision_agent/  # Team 3 — Risk & Decision Agent (active)
    │   └── response_agent/       # Team 4 — Response Agent (stub)
    │
    ├── common/                   # Shared utilities across agents
    │   ├── messaging/            # Inter-agent communication (stub)
    │   ├── mcp/                  # Shared MCP utilities (stub)
    │   ├── cache/                # Shared caching utilities (stub)
    │   └── utils/                # General helpers (stub)
    │
    ├── infrastructure/           # Platform-wide infrastructure
    │   ├── celery.py             # Async task queue (stub)
    │   ├── logging.py            # Centralized logging (stub)
    │   └── monitoring.py         # Health monitoring (stub)
    │
    └── tests/                    # Test directory
```

---

## Agent Structure (Risk & Decision Agent)

Each agent follows a **domain-driven design** with clean separation of concerns:

```
architecture/risk_decision_agent/
├── apps.py                       # Django app config
├── tasks.py                      # Celery async tasks (stub)
│
├── api/                          # REST API layer (public interface)
│   ├── urls.py                   # URL routing for all endpoints
│   ├── views.py                  # DRF APIView classes
│   └── serializers.py            # Input validation & output formatting
│
├── domain/                       # Core business logic (no Django deps)
│   ├── decision_engine.py        # Main DecisionAgent class
│   │                             #   - Context gathering via MCP tools
│   │                             #   - LLM risk analysis (ReAct loop)
│   │                             #   - Bounded risk adjustment
│   │                             #   - Decision output (ALLOW/MONITOR/ESCALATE/BLOCK)
│   ├── reasoning.py              # LLMReasoner — OpenAI-compatible LLM client
│   │                             #   - Prompt construction & JSON parsing
│   │                             #   - TokenFactory integration
│   └── models.py                 # Data classes (event schemas, not ORM models)
│
├── application/                  # Orchestration layer
│   └── orchestration_service.py  # Singleton service bridging API ↔ Domain
│                                 #   - Initializes LLM + Agent once per process
│                                 #   - Thread-safe request handling
│
├── infrastructure/               # External integrations
│   ├── cache/
│   │   └── cache_manager.py      # SQLite-based TTL cache
│   │                             #   - Caches MCP tool results
│   │                             #   - Caches LLM analyses
│   │                             #   - Auto-expiry & cleanup
│   ├── mcp/
│   │   ├── server.py             # MCP stdio server (runs as subprocess)
│   │   ├── client.py             # MCP client (connects to server)
│   │   └── tools/cert_tools/     # CERT database tools (9 files)
│   │       ├── __init__.py
│   │       ├── tool_accessor.py  # CertTools container
│   │       ├── identity.py       # LDAP + psychometrics queries
│   │       ├── telemetry.py      # Email + file activity queries
│   │       ├── rule_library.py   # Rule explanation queries
│   │       ├── parsing.py        # Timestamp parsing utilities
│   │       ├── db.py             # Supabase Postgres connection
│   │       ├── local_policy.py   # Local JSON policy reader
│   │       └── summaries.py      # Activity summarization
│   └── data/local_data/          # Local JSON config files
│       ├── policy_db.json        # Risk thresholds & decision rules
│       └── sample_anomaly_events.json  # Test events
│
├── skills/                       # Deterministic computation (no LLM)
│   ├── __init__.py
│   └── risk_computation.py       # Risk level classification
│                                 #   - classify_risk_level()
│                                 #   - generate_decision()
│                                 #   - recommend_action()
│
└── integrations/                 # Inter-agent communication clients
    ├── data_agent_client.py      # Team 1 client (stub)
    ├── behavior_agent_client.py  # Team 2 client (stub)
    └── response_agent_client.py  # Team 4 client (stub)
```

> **Note:** Other agents (data_agent, behavior_agent, response_agent) follow the same internal structure. They are currently stubs (`__init__.py` only) and will be implemented when their respective teams are ready.

---

## API Endpoints

Base URL: `http://127.0.0.1:8000/`

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/` | API root — lists all available endpoints |
| `GET` | `/api/v1/risk-decision/health/` | Health check |
| `POST` | `/api/v1/risk-decision/analyze/` | Analyze a single anomaly event |
| `POST` | `/api/v1/risk-decision/batch/` | Analyze multiple events |
| `GET` | `/api/v1/risk-decision/sample-events/` | Get sample test events |
| `GET` | `/api/v1/risk-decision/cache/stats/` | View cache statistics |
| `POST` | `/api/v1/risk-decision/cache/clear/` | Clear all cached data |
| `POST` | `/api/v1/risk-decision/cache/cleanup/` | Remove expired entries |

### Example: Analyze an Event

```bash
curl -X POST http://127.0.0.1:8000/api/v1/risk-decision/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "evt-test-0001",
    "user_id": "MOH0273",
    "entity_id": "{L9G8-J9QE34VM-2834VDPB}",
    "timestamp": "2010-01-02T07:23:14",
    "score": 0.87,
    "triggered_rules": ["login_outside_normal_hours", "unknown_device"],
    "confidence": "high",
    "cold_start": false
  }'
```

Or use the **DRF Browsable API** — visit the endpoint in your browser and use the built-in form.

---

## How It Works

1. **Event arrives** via `POST /analyze/` (from Team 2 or frontend)
2. **Context gathering** — 7 MCP tools query Supabase for:
   - User identity (LDAP + psychometrics)
   - Telemetry baseline (30-day email/file history)
   - Current activity summary (last 24h)
   - Behavioral deviations (z-scores vs baseline)
   - Asset metadata (file sensitivity)
   - Policy thresholds
   - Rule explanations
3. **LLM analysis** — Llama-3.1-70B analyzes context and recommends a risk adjustment (±0.3 max)
4. **Deterministic clamping** — Python validates and bounds the adjustment
5. **Decision** — ALLOW / MONITOR / ESCALATE / BLOCK with full reasoning
6. **Response** — JSON with score, decision, risk factors, and explanation

All tool results and LLM analyses are **cached in SQLite** for fast repeated queries.

---

## Environment Variables

Create `cybersec_backend/.env`:

```env
ESPRIT_API_KEY=your_key_here
SUPABASE_DB_URL=postgresql://user:pass@host:port/dbname
DEBUG=True
```

| Variable | Required | Description |
|----------|----------|-------------|
| `ESPRIT_API_KEY` | Yes | API key for the LLM (TokenFactory/OpenAI-compatible) |
| `SUPABASE_DB_URL` | Yes | Postgres connection string for CERT tools |
| `DEBUG` | No | Django debug mode (default: `False`) |
| `DJANGO_SECRET_KEY` | No | Django secret key (auto-generated in dev) |

---

## Testing

```powershell
# Run the smoke test (server must be running)
cd cybersec_backend
python test_api.py
```

Or test individual endpoints in the browser — DRF provides a browsable HTML interface at each URL.

---

## Tech Stack

- **Backend:** Django 6.0 + Django REST Framework
- **LLM:** Llama-3.1-70B via TokenFactory (OpenAI-compatible API)
- **Database:** Supabase Postgres (CERT data) + SQLite (Django ORM + cache)
- **Protocol:** MCP (Model Context Protocol) over stdio for tool calls
- **Frontend:** Next.js (planned — REST API ready for integration)

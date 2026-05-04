# Behavior Agent - Organized Structure

This document describes the organized structure of the Behavior Agent (formerly Monitor A) within the Django project.

## Directory Structure

```
cybersec_backend/
├── architecture/behavior_agent/          # Main behavior agent module
│   ├── api/                              # DRF API endpoints
│   │   ├── views.py                      # API views with dual detection
│   │   ├── serializers.py                # Request/response serializers
│   │   └── urls.py                       # URL routing
│   ├── application/                      # Application layer
│   │   ├── orchestration_service.py      # Main service orchestrator
│   │   └── cache.py                      # In-memory baseline cache
│   ├── core/                            # LangGraph core components
│   │   ├── graph.py                      # LangGraph graph definition
│   │   ├── nodes.py                      # Graph node implementations
│   │   └── state.py                      # AgentState schema
│   ├── scoring/                         # ML scoring components
│   │   ├── baseline.py                   # UserBaseline dataclass
│   │   ├── features.py                   # Feature extraction (18 features)
│   │   ├── model.py                      # IF model loader and inference
│   │   ├── dimensions.py                 # Dimension scoring and rules
│   │   └── update.py                     # Score-gated baseline updates
│   ├── infrastructure/                  # External integrations
│   │   └── mcp/                         # Model Context Protocol
│   │       ├── client.py                # MCP client for LLM context
│   │       └── server.py                # MCP server with 7 tools
│   ├── memory/                          # Persistence layer
│   │   └── checkpointer.py              # LangGraph checkpointer + history
│   ├── integrations/                    # External service clients
│   │   └── risk_decision_client.py      # Team 3 forwarding client
│   └── apps.py                          # Django app configuration
├── data/                                # Model files and datasets
│   ├── if_model_A.pkl                   # Trained Isolation Forest model
│   ├── feature_cols_A.pkl               # Feature column names
│   ├── score_bounds_A.pkl               # Score normalization bounds
│   ├── baselines.sqlite                 # User behavioral baselines (1,001 users)
│   ├── test_sessions.parquet            # CERT r4.2 test sessions
│   ├── insiders.csv                     # Ground truth insider list
│   └── agent_memory.db                  # Session history database
└── config/settings/base.py              # Updated Django settings
```

## Key Features

### 1. **Dual Detection System**
- **IF Model Detection**: Statistical anomaly detection (HIGH priority)
- **LLM Detection**: Contextual threat analysis (MEDIUM priority)
- Both types forward to Risk Decision Agent with appropriate priority

### 2. **Organized Components**
- **Core**: LangGraph pipeline (5 nodes: load → score → update → explain → build)
- **Scoring**: ML model, feature extraction, dimension scoring
- **Infrastructure**: MCP tools for LLM context gathering
- **Memory**: Persistent checkpointing and session history
- **API**: RESTful endpoints with automatic Team 3 forwarding

### 3. **Data Organization**
- All model files consolidated in `cybersec_backend/data/`
- No external dependencies on standalone `monitor_a/` directory
- Self-contained within Django project structure

### 4. **Performance Optimizations**
- In-memory baseline cache (1,001 users loaded at startup)
- Lazy model loading (IF model loaded on first use)
- Score-gated baseline updates (only normal sessions update behavioral stats)

## API Endpoints

- `GET /api/v1/behavior/health/` - Health check
- `POST /api/v1/behavior/score/` - Score single session
- `POST /api/v1/behavior/batch/` - Score multiple sessions
- `GET /api/v1/behavior/baseline/<user_id>/` - Get user baseline
- `GET /api/v1/behavior/history/<user_id>/` - Get user history
- `GET /api/v1/behavior/sample-sessions/` - Get test sessions

## MCP Tools (7 tools)

1. `behavior.baseline.get_user_baseline` - User behavioral stats
2. `behavior.baseline.get_user_history` - Recent session scores
3. `behavior.baseline.get_dept_stats` - Department norms
4. `behavior.session.score_session` - Full scoring pipeline
5. `behavior.session.get_feature_vector` - 18-feature vector
6. `behavior.rules.explain_triggered_rules` - Rule explanations
7. `behavior.policy.get_thresholds` - Detection configuration

## Configuration

All paths now point to the organized structure:
- Model files: `cybersec_backend/data/`
- Settings: `config/settings/base.py`
- No external `MONITOR_A_PATH` environment variable needed

## Migration Complete

✅ All Monitor A components moved and organized
✅ Django settings updated for new paths
✅ Import paths corrected throughout codebase
✅ Data files consolidated in project structure
✅ Self-contained, no external dependencies
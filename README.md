# Cybersecurity Multi-Agent SOC Platform

An AI-powered multi-agent Security Operations Center (SOC) platform for real-time insider threat detection, behavioral anomaly analysis, risk assessment, and automated incident response. Built with **Django**, **Next.js**, **Llama 3.1 LLM**, **LangGraph**, **Isolation Forest ML**, and **Reinforcement Learning**.

---

## Overview

This project was developed as part of the **4th-year Integrated Project** at [Esprit School of Engineering](https://esprit.tn). It explores the design and implementation of a **multi-agent cybersecurity pipeline** that leverages artificial intelligence and machine learning to detect, analyze, and respond to insider threats and cyberattacks in real time.

The platform chains **5 specialized AI agents** in a sequential pipeline, each responsible for a distinct phase of the security operations workflow — from data collection to automated response. Unlike traditional SIEM tools that rely on static rules, our system combines **statistical anomaly detection** (Isolation Forest), **LLM-powered contextual reasoning** (Llama 3.1), and **Reinforcement Learning** (Q-Learning) to make intelligent, context-aware security decisions — with a human-in-the-loop when needed.

**Pipeline Architecture:**
```
Data Agent → Behavior Agent → Risk & Decision Agent → Response Agent
                  ↑
            Attacker Agent (adversarial red-team simulation)
```

---

## Features

- **Dual Detection System** — Combines Isolation Forest ML anomaly detection with LLM contextual threat analysis for higher accuracy
- **5-Agent Security Pipeline** — Data collection, behavioral scoring, risk assessment, and automated response in a real-time streaming pipeline
- **LLM-Powered Risk Reasoning** — Llama-3.1-70B analyzes security context via a ReAct (Reasoning + Acting) loop with 7 MCP tools
- **Hybrid Response Decision-Making** — Three parallel decision engines (LLM Weighting + LLM Direct + RL Model) orchestrated by a final LLM
- **Reinforcement Learning Agent** — Q-Learning model that learns from operator feedback and improves response decisions over time
- **Adversarial Attack Simulation** — LLM-powered 5-phase red-team attack cycle (Observe → List → Analyze → Choose → Inject) mapped to MITRE ATT&CK techniques
- **Human-in-the-Loop via Twilio** — Automated voice calls to security operators for medium-risk event approval
- **Real-Time Dashboard** — Next.js frontend with live pipeline visualization, agent status tracking, and streaming terminal logs
- **Inter-Agent Communication** — MCP (Model Context Protocol) for tool-calling and A2A (Agent-to-Agent) protocol for agent messaging
- **Full Explainability** — Every decision includes a complete reasoning chain from raw data to final action

---

## Tech Stack

### Backend
| Technology | Purpose |
|-----------|---------|
| **Python 3.12** | Core programming language |
| **Django 6.0** | Backend web framework |
| **Django REST Framework** | RESTful API endpoints |
| **Supabase Postgres** | CERT insider threat database (LDAP, telemetry, psychometrics) |
| **SQLite** | Local caching, baselines, Django ORM |

### Frontend
| Technology | Purpose |
|-----------|---------|
| **Next.js (React)** | Frontend framework |
| **TypeScript** | Type-safe frontend development |
| **Framer Motion** | Animations and micro-interactions |
| **Tailwind CSS** | Utility-first styling |

### AI / Machine Learning
| Technology | Purpose |
|-----------|---------|
| **Llama-3.1-70B** | Large Language Model for reasoning and analysis (via TokenFactory API) |
| **LangGraph** | Agent graph pipeline for Behavior Agent (5-node processing graph) |
| **Isolation Forest (scikit-learn)** | Statistical anomaly detection model |
| **Q-Learning (Reinforcement Learning)** | Self-improving response decision model |

### Protocols & Integrations
| Technology | Purpose |
|-----------|---------|
| **MCP (Model Context Protocol)** | Tool-calling protocol for LLM ↔ database interaction |
| **A2A (Agent-to-Agent Protocol)** | Inter-agent communication and event forwarding |
| **SSE (Server-Sent Events)** | Real-time streaming from backend to frontend |
| **Twilio** | Voice calls and SMS for human-in-the-loop approval |
| **MITRE ATT&CK Framework** | Attack technique classification and mapping |

### Other Tools
| Technology | Purpose |
|-----------|---------|
| **CERT r4.2 Dataset** | Carnegie Mellon insider threat dataset for training and testing |
| **Git & GitHub** | Version control and collaboration |
| **npm** | Frontend package management |

---

## Directory Structure

```
Cybersecurity_project-main/
├── README.md                         # This file
│
├── cybersec_backend/                 # Django backend (Python)
│   ├── manage.py                     # Django entry point
│   ├── requirements.txt              # Python dependencies
│   ├── config/                       # Django settings & URL routing
│   │   ├── settings/                 # Dev & prod configuration
│   │   └── urls.py                   # Root URL router
│   ├── architecture/                 # All 5 AI agents
│   │   ├── data_agent/               # Agent 1 — Data collection (MCP + SSE)
│   │   │   ├── agents/               # LLM data engineering agent
│   │   │   ├── collectors/           # Windows, file, network, browser collectors
│   │   │   ├── mcp_servers/          # MCP tool servers
│   │   │   └── api/                  # REST API endpoints
│   │   ├── attacker_agent/           # Agent 2 — Red-team attack simulation
│   │   ├── behavior_agent/           # Agent 3 — Anomaly detection (IF + LLM)
│   │   │   ├── core/                 # LangGraph pipeline (graph, nodes, state)
│   │   │   ├── scoring/              # Isolation Forest model & features
│   │   │   ├── memory/               # Session checkpointing
│   │   │   └── infrastructure/mcp/   # 7 MCP tools for LLM context
│   │   ├── risk_decision_agent/      # Agent 4 — Risk assessment (ReAct loop)
│   │   │   ├── domain/               # Decision engine & LLM reasoning
│   │   │   ├── infrastructure/mcp/   # 9 CERT database tools
│   │   │   └── skills/               # Deterministic risk computation
│   │   └── response_agent/           # Agent 5 — Hybrid response (LLM + RL)
│   │       ├── domain/               # LLM weighting, direct, RL, orchestrator
│   │       ├── infrastructure/       # Twilio client, RL model
│   │       └── skills/               # Action execution engine
│   ├── common/                       # Shared utilities (messaging, cache)
│   └── data/                         # ML models, baselines, datasets
│
├── cybersec_frontend/                # Next.js frontend (TypeScript)
│   ├── app/                          # Pages and routing
│   │   ├── page.tsx                  # Main pipeline dashboard
│   │   └── agents/[slug]/            # Individual agent detail pages
│   ├── components/dashboard/         # UI components
│   │   ├── pipeline-visualization.tsx
│   │   ├── data-agent-live.tsx
│   │   ├── behavior-agent-live.tsx
│   │   ├── risk-agent-live.tsx
│   │   ├── response-agent-test.tsx
│   │   ├── attacker-agent-live.tsx
│   │   ├── terminal-logs.tsx
│   │   └── stats-cards.tsx
│   └── lib/                          # API clients & state management
│
└── agents/                           # Agent state persistence
```

---

## Getting Started

### Prerequisites

- **Python 3.12+** — Backend runtime
- **Node.js 18+** — Frontend runtime
- **npm** — Frontend package manager
- **Git** — Version control

### Backend Setup

```powershell
# Navigate to backend
cd cybersec_backend

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install Python dependencies
pip install -r requirements.txt

# Configure environment variables
# Create .env file with:
#   ESPRIT_API_KEY=your_llm_api_key
#   SUPABASE_DB_URL=postgresql://user:pass@host:port/dbname

# Run database migrations
python manage.py migrate

# Start the backend server
python manage.py runserver 8000
```

Backend API available at: `http://localhost:8000/`

### Frontend Setup

```powershell
# Navigate to frontend
cd cybersec_frontend

# Install Node.js dependencies
npm install

# Start the development server
npm run dev
```

Frontend dashboard available at: `http://localhost:3000/`

### Running the Pipeline

1. Start the backend server (port 8000)
2. Start the frontend server (port 3000)
3. Open `http://localhost:3000` in your browser
4. Select pipeline mode: **Test Sessions** or **Real Data Collection**
5. Select pipeline source: **Data Agent** or **Attacker Agent**
6. Click **Run Pipeline** and observe real-time agent execution

---

## API Endpoints

### Data Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/data/health/` | Health check |
| `POST` | `/api/v1/data/collect/` | Collect security events |
| `POST` | `/api/v1/data/collect-stream/` | Collect with SSE streaming |
| `POST` | `/api/v1/data/query/` | Query stored events |
| `POST` | `/api/v1/data/analyze/` | LLM event analysis |
| `POST` | `/api/v1/data/inject-attack/` | Inject test attack events |
| `GET` | `/api/v1/data/stats/` | Collection statistics |

### Behavior Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/behavior/health/` | Health check |
| `POST` | `/api/v1/behavior/score/` | Score single session |
| `POST` | `/api/v1/behavior/batch/` | Batch score sessions |
| `GET` | `/api/v1/behavior/baseline/<user_id>/` | Get user baseline |
| `GET` | `/api/v1/behavior/sample-sessions/` | Get test sessions |

### Risk & Decision Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/risk-decision/health/` | Health check |
| `POST` | `/api/v1/risk-decision/analyze/` | Analyze anomaly event |
| `POST` | `/api/v1/risk-decision/batch/` | Batch analysis |
| `GET` | `/api/v1/risk-decision/cache/stats/` | Cache statistics |

### Response Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/response/health/` | Health check |
| `POST` | `/api/v1/response/process/` | Process risk output → final decision |
| `POST` | `/api/v1/response/approval/` | Handle Twilio user approval |
| `POST` | `/api/v1/response/train/` | Train RL model from feedback |
| `GET` | `/api/v1/response/rl/stats/` | RL model statistics |

---

## How It Works

1. **Data Collection** — The Data Agent collects security events from Windows logs, file systems, network traffic, and browser activity via MCP servers
2. **Session Aggregation** — Raw events are aggregated into user sessions with 18 behavioral features
3. **Anomaly Detection** — The Behavior Agent scores each session using an Isolation Forest model and LLM contextual analysis (dual detection)
4. **Risk Assessment** — Flagged sessions are forwarded to the Risk & Decision Agent, which gathers context via 7 MCP tools and performs LLM ReAct reasoning
5. **Decision** — The Risk Agent produces a bounded decision: ALLOW / MONITOR / ESCALATE / BLOCK
6. **Automated Response** — The Response Agent combines 3 decision engines (LLM Weighting + LLM Direct + RL Model) and executes the appropriate action
7. **Human-in-the-Loop** — For medium-risk events, a Twilio voice call is placed to the security operator for approval

---

## Acknowledgments

This project was developed as part of the **4th-year Integrated Project (Projet Intégré)** at [Esprit School of Engineering](https://esprit.tn) (École Supérieure Privée d'Ingénierie et de Technologies), Tunisia.

We would like to thank:
- **Esprit School of Engineering** for providing the academic framework and resources
- Our **academic and professional mentors** for their guidance throughout the project
- The **Carnegie Mellon CERT Division** for the CERT r4.2 insider threat dataset used in training and evaluation

---

## License

This project is part of the academic curriculum at **Esprit School of Engineering**. All rights reserved.

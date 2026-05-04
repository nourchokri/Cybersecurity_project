# Working on the Integrated Project

This guide is for working on the integrated Django project at:
`C:\Users\moham\Desktop\project_classe-main\project_classe-main\cybersec_backend`

## Project Structure

```
cybersec_backend/
├── architecture/
│   ├── data_agent/           ← YOUR AGENT (Monitor B)
│   │   ├── agents/           ← Your LLM agent
│   │   ├── mcp_servers/      ← Your MCP servers
│   │   ├── collectors/       ← Your data collectors
│   │   ├── data/             ← Attack patterns
│   │   ├── api/              ← Django REST API
│   │   ├── application/      ← Business logic
│   │   └── infrastructure/   ← MCP integration
│   ├── behavior_agent/       ← Team 1 (Monitor A)
│   ├── risk_decision_agent/  ← Team 3
│   └── response_agent/       ← Team 4 (pending)
├── config/                   ← Django settings & URLs
├── common/                   ← Shared utilities
└── manage.py                 ← Django management
```

## Your Data Agent APIs

All your endpoints are under `/api/v1/data/`:

### 1. Health Check
```bash
GET http://localhost:8000/api/v1/data/health/
```

### 2. Collect Events
```bash
POST http://localhost:8000/api/v1/data/collect/
Content-Type: application/json

{
  "collectors": ["file", "network"]  # optional, empty = all
}
```

### 3. Query Events
```bash
POST http://localhost:8000/api/v1/data/query/
Content-Type: application/json

{
  "start_date": "2026-04-01",
  "end_date": "2026-04-26",
  "event_type": "file_access",
  "limit": 100
}
```

### 4. Analyze Events (LLM)
```bash
POST http://localhost:8000/api/v1/data/analyze/
Content-Type: application/json

{
  "query": "Find suspicious file access patterns",
  "start_date": "2026-04-01",
  "max_events": 100
}
```

### 5. Inject Test Attacks
```bash
POST http://localhost:8000/api/v1/data/inject-attack/
Content-Type: application/json

{
  "attack_type": "data_exfiltration",
  "count": 5
}
```

### 6. Get Statistics
```bash
GET http://localhost:8000/api/v1/data/stats/
```

## Running the Platform

### Backend (Django)
```powershell
cd C:\Users\moham\Desktop\project_classe-main\project_classe-main\cybersec_backend
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

Backend runs at: **http://localhost:8000**

### Frontend (Next.js)
```powershell
cd C:\Users\moham\Desktop\project_classe-main\project_classe-main\cybersec_frontend
npm run dev
```

Frontend runs at: **http://localhost:3000**

## Making Changes to Your Agent

### Modifying API Endpoints
Edit: `architecture/data_agent/api/views.py`

### Modifying Business Logic
Edit: `architecture/data_agent/application/data_service.py`

### Modifying MCP Integration
Edit: `architecture/data_agent/infrastructure/mcp_integration.py`

### Adding New Collectors
Add to: `architecture/data_agent/collectors/`

### Modifying MCP Servers
Edit: `architecture/data_agent/mcp_servers/`

### Modifying LLM Agent
Edit: `architecture/data_agent/agents/llm_data_engineering_agent.py`

## Important Files

### Configuration
- `.env` - Environment variables (Supabase, OpenAI keys)
- `architecture/data_agent/mcp_config.json` - MCP server configuration
- `architecture/data_agent/agents/config.json` - Agent configuration

### URLs
- `config/urls.py` - Main URL routing (includes your data_agent URLs)
- `architecture/data_agent/api/urls.py` - Your agent's URL patterns

## Testing Your Changes

After making changes:

1. **Restart Django server** (CTRL+C, then `python manage.py runserver`)
2. **Test health endpoint**: `curl http://localhost:8000/api/v1/data/health/`
3. **Check frontend**: Open http://localhost:3000

## Common Issues

### "No module named 'agents'"
- Make sure you're in the right directory
- Check that `architecture/data_agent/agents/` exists

### "signal only works in main thread"
- This is fixed with lazy initialization
- Don't initialize MCP clients on import

### MCP Connection Errors
- Check `architecture/data_agent/mcp_config.json`
- Verify server names use underscores: `collector_executor`, not `collector-executor`

### Frontend Can't Collect Real Data
The frontend needs to be updated to call your data_agent endpoints. Check:
- `cybersec_frontend/components/` - Frontend components
- `cybersec_frontend/lib/` - API client code

You may need to add a new component or update existing ones to call:
```javascript
fetch('http://localhost:8000/api/v1/data/collect/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ collectors: [] })
})
```

## Syncing Changes Back to Your Original Project

If you make improvements in the integrated project and want to copy them back:

```powershell
# Copy data_agent back to your original project
Copy-Item -Recurse C:\Users\moham\Desktop\project_classe-main\project_classe-main\cybersec_backend\architecture\data_agent\agents C:\Users\moham\Desktop\cybersec_project-main\
Copy-Item -Recurse C:\Users\moham\Desktop\project_classe-main\project_classe-main\cybersec_backend\architecture\data_agent\mcp_servers C:\Users\moham\Desktop\cybersec_project-main\
Copy-Item -Recurse C:\Users\moham\Desktop\project_classe-main\project_classe-main\cybersec_backend\architecture\data_agent\collectors C:\Users\moham\Desktop\cybersec_project-main\
```

## Working with Kiro

When opening the integrated project in Kiro:

1. **Open the backend folder**: 
   - File → Open Folder
   - Select: `C:\Users\moham\Desktop\project_classe-main\project_classe-main\cybersec_backend`

2. **Your agent is in**: `architecture/data_agent/`

3. **Tell Kiro**: "I'm working on the data_agent which is Monitor B for data exfiltration detection. It's integrated into a Django multi-agent platform."

## Next Steps

1. **Update frontend** to call your data_agent APIs
2. **Add forwarding logic** to send suspicious events to risk_decision_agent
3. **Test end-to-end** workflow with all agents
4. **Add monitoring/logging** for production

## Questions?

- Check `architecture/data_agent/README.md` for API documentation
- Check `INTEGRATION_GUIDE.md` for integration details
- Ask your teammates about their agent interfaces

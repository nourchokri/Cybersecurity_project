# Frontend Display Issue - Debug Files Reference

## Problem Description
When testing with real data, the workflow from Behavioral Agent → Risk Agent is working on the backend, but the frontend is NOT displaying the results properly. This was working perfectly in `project_classe-main`.

## Key Files to Review

### 1. Frontend Components (Working Version)

#### Main Agent Page
**File:** `cybersec_frontend/app/agents/[slug]/page.tsx`
- Handles routing for different agents (behavior-agent, risk-behavior-agent, data-agent)
- Manages live logs and dynamic metrics
- Conditionally renders different components based on agent slug

#### Risk Agent Live Component
**File:** `cybersec_frontend/components/dashboard/risk-agent-live.tsx`
- Displays risk analysis results
- Handles event selection and analysis
- Shows decision output (ALLOW, MONITOR, ESCALATE, BLOCK)
- Displays risk levels (LOW, MEDIUM, HIGH)
- Key features:
  - Sample event selector
  - "Run Analysis" button
  - Result tabs (Summary, JSON, Details)
  - Real-time logging integration

#### Behavior Agent Live Component
**File:** `cybersec_frontend/components/dashboard/behavior-agent-live.tsx`
- Displays behavior scoring results
- Handles session selection from test_sessions.parquet
- Shows anomaly detection results
- Key features:
  - Session selector with filtering (all/flagged only)
  - "Score Session" button
  - Dimension breakdown visualization
  - Triggered rules display
  - LLM analysis notes

#### API Client Library
**File:** `cybersec_frontend/lib/api.ts`
- Contains all API communication logic
- Base URL: `process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"`
- Key functions:
  - `analyzeEvent(event)` - POST /api/v1/risk-decision/analyze/
  - `scoreBehaviorSession(session)` - POST /api/v1/behavior/score/
  - `getSampleEvents()` - GET /api/v1/risk-decision/sample-events/
  - `getSampleBehaviorSessions(n, flaggedOnly)` - GET /api/v1/behavior/sample-sessions/
  - `pipelineCollectData(collectors)` - POST /api/v1/data/pipeline-collect/ (10min timeout)

### 2. Backend API Endpoints (Working Version)

#### Risk Decision Agent Views
**File:** `cybersec_backend/architecture/risk_decision_agent/api/views.py`
- `AnalyzeEventView` - POST /api/v1/risk-decision/analyze/
- `SampleEventsView` - GET /api/v1/risk-decision/sample-events/
- `BatchAnalyzeView` - POST /api/v1/risk-decision/batch/

#### Behavior Agent Views
**File:** `cybersec_backend/architecture/behavior_agent/api/views.py`
- `ScoreSessionView` - POST /api/v1/behavior/score/
- `SampleSessionsView` - GET /api/v1/behavior/sample-sessions/
- `BatchScoreView` - POST /api/v1/behavior/batch/

#### Data Agent Views (Pipeline)
**File:** `cybersec_backend/architecture/data_agent/api/views.py`
- `PipelineCollectView` - POST /api/v1/data/pipeline-collect/
  - This is the critical endpoint that orchestrates the full pipeline
  - Collects data → Creates sessions → Scores behavior → Analyzes risk

### 3. Environment Configuration

#### Frontend Environment
**File:** `cybersec_frontend/.env.local`
- Check `NEXT_PUBLIC_API_URL` setting
- Should point to backend (e.g., http://127.0.0.1:8000)

#### Backend Environment
**File:** `cybersec_backend/.env`
- Database connections
- API keys for LLM services
- CORS settings

### 4. URL Routing

#### Backend URLs
**File:** `cybersec_backend/config/urls.py`
- Defines all API route patterns
- Check that all agent endpoints are properly registered

## Common Issues to Check

### 1. API Base URL Mismatch
- Frontend `NEXT_PUBLIC_API_URL` must match backend server address
- Check if backend is running on correct port (default: 8000)
- Verify CORS settings allow frontend origin

### 2. Response Format Differences
- Compare response structure from working vs non-working backend
- Check if field names match between backend response and frontend expectations
- Verify TypeScript interfaces in `api.ts` match actual API responses

### 3. State Management Issues
- Check if `useState` hooks are properly updating
- Verify `useEffect` dependencies are correct
- Ensure callbacks (`onLog`, `onAnalysisComplete`) are being called

### 4. Component Rendering Conditions
- Verify `agentSlug` matches expected values ("behavior-agent", "risk-behavior-agent")
- Check if conditional rendering logic is correct
- Ensure data is not null/undefined before rendering

### 5. Pipeline Flow Issues
- Data Agent → Behavior Agent → Risk Agent
- Check if intermediate results are being passed correctly
- Verify the `behavior_result` field in pipeline response contains expected data

## Testing Steps

### 1. Test Backend Endpoints Directly
```bash
# Test Risk Agent
curl -X POST http://127.0.0.1:8000/api/v1/risk-decision/analyze/ \
  -H "Content-Type: application/json" \
  -d '{"event_id":"test","user_id":"user123","score":0.8}'

# Test Behavior Agent
curl -X POST http://127.0.0.1:8000/api/v1/behavior/score/ \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user123","hour_of_day":14,"file_count":50}'

# Test Pipeline
curl -X POST http://127.0.0.1:8000/api/v1/data/pipeline-collect/ \
  -H "Content-Type: application/json" \
  -d '{"collectors":[]}'
```

### 2. Check Browser Console
- Open DevTools → Console tab
- Look for JavaScript errors
- Check Network tab for failed API requests
- Verify response payloads match expected format

### 3. Check Backend Logs
- Look for errors in Django console
- Verify requests are reaching the backend
- Check if responses are being sent correctly

### 4. Compare Working vs Non-Working
- Export sample API responses from working version
- Compare with responses from non-working version
- Identify any structural differences

## Files to Copy to Other AI

Copy these files from `project_classe-main` to compare with `cybersec_project_copy`:

1. **Frontend:**
   - `cybersec_frontend/lib/api.ts`
   - `cybersec_frontend/components/dashboard/risk-agent-live.tsx`
   - `cybersec_frontend/components/dashboard/behavior-agent-live.tsx`
   - `cybersec_frontend/app/agents/[slug]/page.tsx`
   - `cybersec_frontend/.env.local`

2. **Backend:**
   - `cybersec_backend/architecture/risk_decision_agent/api/views.py`
   - `cybersec_backend/architecture/behavior_agent/api/views.py`
   - `cybersec_backend/architecture/data_agent/api/views.py`
   - `cybersec_backend/config/urls.py`

3. **Reference:**
   - `PIPELINE_FIX_REFERENCE/` folder (if exists)

## Quick Diagnostic Commands

```bash
# Check if backend is running
curl http://127.0.0.1:8000/api/v1/risk-decision/health/

# Check if frontend can reach backend
# (Run in browser console on frontend page)
fetch('http://127.0.0.1:8000/api/v1/risk-decision/health/')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)

# Check CORS headers
curl -I -X OPTIONS http://127.0.0.1:8000/api/v1/risk-decision/analyze/ \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST"
```

## Expected Workflow

1. **Data Agent** collects raw events
2. **Data Agent** creates behavior sessions from events
3. **Behavior Agent** scores each session (via `/api/v1/behavior/score/`)
4. **Risk Agent** analyzes flagged sessions (via `/api/v1/risk-decision/analyze/`)
5. **Frontend** displays results in real-time

The issue is likely in step 5 - the backend is working but frontend is not displaying the results.

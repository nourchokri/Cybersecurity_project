# Complete Debug Package - Frontend Display Issue

## Problem Summary
**Working:** `project_classe-main` - Behavioral Agent → Risk Agent workflow displays results correctly in frontend
**Not Working:** `cybersec_project_copy` - Same workflow works on backend but frontend doesn't display results

## Architecture Overview

### Data Flow
```
Data Agent (Team 1)
    ↓ collects events
    ↓ creates sessions
Behavior Agent (Team 2 - Monitor A)
    ↓ scores sessions
    ↓ forwards flagged sessions
Risk Decision Agent (Team 3)
    ↓ analyzes risk
    ↓ makes decision
Frontend Display
    ✓ Working in project_classe-main
    ✗ Not working in cybersec_project_copy
```

### API Endpoints

#### Behavior Agent (Team 2)
- **POST** `/api/v1/behavior/score/` - Score a single session
- **POST** `/api/v1/behavior/batch/` - Score multiple sessions
- **GET** `/api/v1/behavior/sample-sessions/?n=30&flagged=1` - Get test data
- **GET** `/api/v1/behavior/baseline/<user_id>/` - Get user baseline
- **GET** `/api/v1/behavior/history/<user_id>/?limit=10` - Get user history

#### Risk Decision Agent (Team 3)
- **POST** `/api/v1/risk-decision/analyze/` - Analyze a single event
- **POST** `/api/v1/risk-decision/batch/` - Analyze multiple events
- **GET** `/api/v1/risk-decision/sample-events/` - Get test events

#### Data Agent (Team 1)
- **POST** `/api/v1/data/pipeline-collect/` - Full pipeline (10min timeout)

## Key Files Reference

### Frontend Files (Working Version)

#### 1. API Client (`lib/api.ts`)
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// Key functions:
- analyzeEvent(event: AnomalyEvent): Promise<DecisionOutput>
- scoreBehaviorSession(session: SessionInput): Promise<BehaviorAnomalyResult>
- getSampleEvents(): Promise<SampleEventsResponse>
- getSampleBehaviorSessions(n, flaggedOnly): Promise<{sessions, total}>
- pipelineCollectData(collectors): Promise<DataCollectionResult>
```

**Critical:** 10-minute timeout for pipeline endpoint:
```typescript
timeout: 600000, // 10 minutes for full pipeline
```

#### 2. Risk Agent Component (`components/dashboard/risk-agent-live.tsx`)
Key state variables:
```typescript
const [decision, setDecision] = useState<DecisionOutput | null>(null)
const [sampleEvents, setSampleEvents] = useState<AnomalyEvent[]>([])
const [selectedEventIndex, setSelectedEventIndex] = useState(0)
const [loading, setLoading] = useState(false)
```

Key logic:
```typescript
const handleAnalyze = async () => {
  const event = sampleEvents[selectedEventIndex]
  const result = await analyzeEvent(event)
  setDecision(result)  // ← This updates the display
  setActiveTab("summary")
}
```

Display conditions:
```typescript
{decision && (
  <Card>
    {/* Shows decision result */}
  </Card>
)}
```

#### 3. Behavior Agent Component (`components/dashboard/behavior-agent-live.tsx`)
Key state variables:
```typescript
const [result, setResult] = useState<BehaviorAnomalyResult | null>(null)
const [sessions, setSessions] = useState<SessionInput[]>([])
const [selectedIdx, setSelectedIdx] = useState(0)
const [flaggedOnly, setFlaggedOnly] = useState(false)
```

Key logic:
```typescript
const handleScore = async () => {
  const session = sessions[selectedIdx]
  const res = await scoreBehaviorSession(session)
  setResult(res)  // ← This updates the display
  setActiveTab("summary")
}
```

Display conditions:
```typescript
{result && analysis && (
  <Card>
    {/* Shows behavior result */}
  </Card>
)}
```

#### 4. Agent Page Router (`app/agents/[slug]/page.tsx`)
Conditional rendering based on agent slug:
```typescript
{slug === "risk-behavior-agent" ? (
  <RiskAgentLiveOutput 
    agentSlug={slug} 
    onLog={handleLog} 
    onAnalysisComplete={handleAnalysisComplete} 
  />
) : slug === "behavior-agent" ? (
  <BehaviorAgentLive 
    agentSlug={slug} 
    onLog={handleLog} 
    onAnalysisComplete={handleAnalysisComplete} 
  />
) : (
  <AgentOutput agentSlug={slug} />
)}
```

### Backend Files (Working Version)

#### 1. Behavior Agent Views (`architecture/behavior_agent/api/views.py`)

**ScoreSessionView** - POST `/api/v1/behavior/score/`
```python
def post(self, request):
    serializer = SessionInputSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': 'Invalid session data'}, status=400)
    
    service = get_orchestration_service()
    result = service.score_session(serializer.validated_data)
    
    if not result.get('ok'):
        return Response({'error': result.get('error')}, status=500)
    
    ar = result['anomaly_result']
    
    # Auto-forward to Risk Agent if flagged
    if ar.get('flagged') or _check_llm_threat_detection(ar):
        priority = 'HIGH' if ar.get('flagged') else 'MEDIUM'
        _forward_to_risk_agent(ar, priority=priority)
    
    return Response(ar, status=200)
```

**SampleSessionsView** - GET `/api/v1/behavior/sample-sessions/`
```python
def get(self, request):
    n = int(request.query_params.get('n', 30))
    flagged = request.query_params.get('flagged', '0') == '1'
    
    # Load from test_sessions.parquet
    df = pd.read_parquet(str(path))
    
    if flagged:
        # Return only sessions with anomalous signals
        mask = (
            (df['usb_connected'] == 1) |
            (df['visited_exfil_domain'] == 1) |
            (df['has_ext_email'] == 1) |
            (df['is_outside_hours'] == 1)
        )
        sample = df[mask].sample(min(n, mask.sum()))
    else:
        # Return mix: 60% anomalous, 40% normal
        ...
    
    return Response({'sessions': sessions, 'total': len(sessions)})
```

#### 2. Risk Decision Agent Views (`architecture/risk_decision_agent/api/views.py`)

**AnalyzeEventView** - POST `/api/v1/risk-decision/analyze/`
```python
def post(self, request):
    serializer = AnomalyEventSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': 'Invalid event data'}, status=400)
    
    service = get_orchestration_service()
    result = service.analyze_event(serializer.validated_data)
    
    if result.get("ok"):
        output = DecisionOutputSerializer(result["decision"])
        return Response(output.data, status=200)
    else:
        return Response({'error': result.get("error")}, status=500)
```

**SampleEventsView** - GET `/api/v1/risk-decision/sample-events/`
```python
def get(self, request):
    service = get_orchestration_service()
    events = service.get_sample_events()
    return Response({"events": events}, status=200)
```

#### 3. URL Configuration (`config/urls.py`)
```python
urlpatterns = [
    path("api/v1/risk-decision/", include("architecture.risk_decision_agent.api.urls")),
    path("api/v1/behavior/", include("architecture.behavior_agent.api.urls")),
    path("api/v1/data/", include("architecture.data_agent.api.urls")),
]
```

## Response Formats

### Behavior Agent Response (`BehaviorAnomalyResult`)
```json
{
  "event_id": "evt_123",
  "timestamp": "2024-01-15T14:30:00Z",
  "user_id": "user_456",
  "combined_score": 0.85,
  "if_score": 0.82,
  "flagged": true,
  "confidence": "high",
  "cold_start": false,
  "triggered_rules": ["usb_connected", "after_hours"],
  "dimension_scores": {
    "time": 0.75,
    "device": 0.90,
    "volume": 0.60,
    "sensitivity": 0.80
  },
  "detection_agent_analysis": {
    "model": "IsolationForest",
    "llm_used": true,
    "analyst_note": "Suspicious activity detected...",
    "scoring_mode": "baseline",
    "score": 0.82,
    "threshold": 0.65,
    "verdict": "HIGH",
    "triggered_signals": ["usb_connected", "after_hours"],
    "dimension_breakdown": {...},
    "session_summary": {...},
    "baseline_context": {...}
  }
}
```

### Risk Decision Agent Response (`DecisionOutput`)
```json
{
  "event_id": "evt_123",
  "timestamp": "2024-01-15T14:30:00Z",
  "user_id": "user_456",
  "entity_id": "asset_789",
  "base_score": 0.85,
  "risk_adjustment": 0.10,
  "adjusted_risk_score": 0.95,
  "risk_level": "HIGH",
  "decision": "ESCALATE",
  "recommended_action": "Immediate investigation required",
  "base_score_analysis": "High anomaly score from behavior analysis...",
  "risk_factors": ["USB device", "After hours", "High sensitivity data"],
  "mitigating_factors": [],
  "adjustment_reasoning": "Asset contains PII, increasing risk...",
  "decision_reasoning": "Multiple high-risk factors warrant escalation...",
  "context_summary": {
    "asset_sensitivity": "HIGH",
    "asset_data_type": "PII",
    "recent_incidents": [],
    "triggered_rules_count": 2
  },
  "confidence": "high",
  "computation_method": "llm",
  "llm_driven": true
}
```

## Common Issues & Solutions

### Issue 1: Frontend Not Displaying Results
**Symptoms:** Backend returns data, but UI shows nothing

**Check:**
1. Browser console for errors
2. Network tab - verify response structure
3. Component state updates - add `console.log(result)` after API call
4. Conditional rendering - verify `decision !== null` or `result !== null`

**Solution:**
```typescript
// Add debugging
const handleAnalyze = async () => {
  const result = await analyzeEvent(event)
  console.log('API Response:', result)  // ← Add this
  setDecision(result)
  console.log('State updated:', result)  // ← Add this
}
```

### Issue 2: API Base URL Mismatch
**Symptoms:** Network errors, CORS issues

**Check:**
```bash
# Frontend .env.local
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000

# Verify backend is running
curl http://127.0.0.1:8000/api/v1/behavior/health/
```

**Solution:** Ensure environment variable is set and backend is accessible

### Issue 3: Response Structure Mismatch
**Symptoms:** TypeScript errors, undefined properties

**Check:** Compare actual API response with TypeScript interface

**Solution:** Update interfaces in `lib/api.ts` to match backend response

### Issue 4: Component Not Rendering
**Symptoms:** Blank screen, no errors

**Check:**
```typescript
// Verify agentSlug matches expected values
console.log('Agent Slug:', slug)  // Should be "behavior-agent" or "risk-behavior-agent"

// Verify conditional rendering
const isBehaviorAgent = agentSlug === "behavior-agent"
console.log('Is Behavior Agent:', isBehaviorAgent)
```

**Solution:** Ensure slug matches exactly (case-sensitive)

### Issue 5: State Not Updating
**Symptoms:** API call succeeds but UI doesn't update

**Check:**
```typescript
// Verify state setter is called
setResult(res)
console.log('Result state:', result)  // May still be null due to async

// Use useEffect to track state changes
useEffect(() => {
  console.log('Result changed:', result)
}, [result])
```

**Solution:** Ensure state setters are called and component re-renders

## Testing Checklist

### Backend Tests
```bash
# 1. Health check
curl http://127.0.0.1:8000/api/v1/behavior/health/

# 2. Get sample sessions
curl http://127.0.0.1:8000/api/v1/behavior/sample-sessions/?n=1

# 3. Score a session
curl -X POST http://127.0.0.1:8000/api/v1/behavior/score/ \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user123","hour_of_day":14,"file_count":50,"duration_minutes":60,"max_sensitivity":2,"usb_connected":0,"has_ext_email":0,"visited_exfil_domain":0,"is_outside_hours":0,"is_weekend":0,"email_count":5}'

# 4. Get sample events
curl http://127.0.0.1:8000/api/v1/risk-decision/sample-events/

# 5. Analyze an event
curl -X POST http://127.0.0.1:8000/api/v1/risk-decision/analyze/ \
  -H "Content-Type: application/json" \
  -d '{"event_id":"test","user_id":"user123","score":0.8,"timestamp":"2024-01-15T14:30:00Z"}'
```

### Frontend Tests
```javascript
// Run in browser console on frontend page

// 1. Test API connectivity
fetch('http://127.0.0.1:8000/api/v1/behavior/health/')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)

// 2. Test sample sessions
fetch('http://127.0.0.1:8000/api/v1/behavior/sample-sessions/?n=1')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)

// 3. Test scoring
fetch('http://127.0.0.1:8000/api/v1/behavior/score/', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    user_id: 'user123',
    hour_of_day: 14,
    file_count: 50,
    duration_minutes: 60,
    max_sensitivity: 2,
    usb_connected: 0,
    has_ext_email: 0,
    visited_exfil_domain: 0,
    is_outside_hours: 0,
    is_weekend: 0,
    email_count: 5
  })
})
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)
```

### Component Tests
```typescript
// Add to component for debugging

useEffect(() => {
  console.log('Component mounted, agentSlug:', agentSlug)
}, [])

useEffect(() => {
  console.log('Sessions loaded:', sessions.length)
}, [sessions])

useEffect(() => {
  console.log('Result updated:', result)
}, [result])
```

## Files to Compare

Compare these files between `project_classe-main` (working) and `cybersec_project_copy` (not working):

### Frontend
- [ ] `lib/api.ts` - API client and type definitions
- [ ] `components/dashboard/behavior-agent-live.tsx` - Behavior display
- [ ] `components/dashboard/risk-agent-live.tsx` - Risk display
- [ ] `app/agents/[slug]/page.tsx` - Agent router
- [ ] `.env.local` - Environment variables

### Backend
- [ ] `architecture/behavior_agent/api/views.py` - Behavior endpoints
- [ ] `architecture/risk_decision_agent/api/views.py` - Risk endpoints
- [ ] `config/urls.py` - URL routing
- [ ] `.env` - Backend configuration

## Quick Diagnostic Script

Save as `diagnose.js` and run in browser console:

```javascript
async function diagnose() {
  const API_BASE = 'http://127.0.0.1:8000';
  const results = {};
  
  // Test 1: Backend health
  try {
    const health = await fetch(`${API_BASE}/api/v1/behavior/health/`).then(r => r.json());
    results.backend_health = '✓ OK';
    console.log('✓ Backend health:', health);
  } catch (e) {
    results.backend_health = '✗ FAIL: ' + e.message;
    console.error('✗ Backend health failed:', e);
  }
  
  // Test 2: Sample sessions
  try {
    const sessions = await fetch(`${API_BASE}/api/v1/behavior/sample-sessions/?n=1`).then(r => r.json());
    results.sample_sessions = `✓ OK (${sessions.total} sessions)`;
    console.log('✓ Sample sessions:', sessions);
  } catch (e) {
    results.sample_sessions = '✗ FAIL: ' + e.message;
    console.error('✗ Sample sessions failed:', e);
  }
  
  // Test 3: Score session
  try {
    const score = await fetch(`${API_BASE}/api/v1/behavior/score/`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        user_id: 'test_user',
        hour_of_day: 14,
        file_count: 50,
        duration_minutes: 60,
        max_sensitivity: 2,
        usb_connected: 0,
        has_ext_email: 0,
        visited_exfil_domain: 0,
        is_outside_hours: 0,
        is_weekend: 0,
        email_count: 5
      })
    }).then(r => r.json());
    results.score_session = '✓ OK';
    console.log('✓ Score session:', score);
  } catch (e) {
    results.score_session = '✗ FAIL: ' + e.message;
    console.error('✗ Score session failed:', e);
  }
  
  console.table(results);
  return results;
}

diagnose();
```

## Next Steps

1. **Read this document** to understand the architecture
2. **Run diagnostic tests** to verify backend is working
3. **Compare files** between working and non-working projects
4. **Check browser console** for JavaScript errors
5. **Add debug logging** to track data flow
6. **Verify environment variables** are set correctly
7. **Test API endpoints** directly with curl
8. **Check component rendering** with console.log statements

## Contact Points

If you need more information about specific components:
- **API Client:** Check `lib/api.ts` for all API functions
- **Behavior Display:** Check `components/dashboard/behavior-agent-live.tsx`
- **Risk Display:** Check `components/dashboard/risk-agent-live.tsx`
- **Backend Logic:** Check `architecture/*/api/views.py` files
- **URL Routing:** Check `config/urls.py`

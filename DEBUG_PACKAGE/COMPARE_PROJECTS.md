# Project Comparison Guide

## Files to Compare Between Projects

Compare these files between `project_classe-main` (working) and `cybersec_project_copy` (not working):

### Critical Frontend Files

```
project_classe-main/cybersec_frontend/lib/api.ts
↕️
cybersec_project_copy/lib/api.ts (or similar path)
```

```
project_classe-main/cybersec_frontend/components/dashboard/risk-agent-live.tsx
↕️
cybersec_project_copy/components/dashboard/risk-agent-live.tsx
```

```
project_classe-main/cybersec_frontend/components/dashboard/behavior-agent-live.tsx
↕️
cybersec_project_copy/components/dashboard/behavior-agent-live.tsx
```

```
project_classe-main/cybersec_frontend/app/agents/[slug]/page.tsx
↕️
cybersec_project_copy/app/agents/[slug]/page.tsx
```

### Environment Files

```
project_classe-main/cybersec_frontend/.env.local
↕️
cybersec_project_copy/.env (or .env.local)
```

### Backend API Files

```
project_classe-main/cybersec_backend/architecture/risk_decision_agent/api/views.py
↕️
cybersec_project_copy/agents/risk_decision_agent/api/views.py (or similar)
```

```
project_classe-main/cybersec_backend/architecture/behavior_agent/api/views.py
↕️
cybersec_project_copy/agents/behavior_agent/api/views.py (or similar)
```

## Key Differences to Look For

### 1. API Base URL
**Working (project_classe-main):**
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
```

**Check in non-working project:**
- Is the environment variable set correctly?
- Is the default fallback correct?
- Is the backend actually running on that port?

### 2. Response Type Definitions
Check if TypeScript interfaces match actual API responses:

```typescript
export interface DecisionOutput {
  event_id: string;
  timestamp: string;
  user_id: string;
  entity_id: string;
  base_score: number;
  risk_adjustment: number;
  adjusted_risk_score: number;
  risk_level: string; // LOW | MEDIUM | HIGH
  decision: string; // ALLOW | MONITOR | ESCALATE | BLOCK
  // ... more fields
}
```

### 3. Component State Management
Check if state updates are working:

```typescript
const [decision, setDecision] = useState<DecisionOutput | null>(null)
const [result, setResult] = useState<BehaviorAnomalyResult | null>(null)
```

### 4. API Call Implementation
Compare the actual API call logic:

```typescript
const result = await analyzeEvent(event)
setDecision(result)
```

### 5. Conditional Rendering
Check if components are being rendered:

```typescript
{slug === "risk-behavior-agent" ? (
  <RiskAgentLiveOutput agentSlug={slug} onLog={handleLog} onAnalysisComplete={handleAnalysisComplete} />
) : slug === "behavior-agent" ? (
  <BehaviorAgentLive agentSlug={slug} onLog={handleLog} onAnalysisComplete={handleAnalysisComplete} />
) : (
  <AgentOutput agentSlug={slug} />
)}
```

## Debugging Checklist

- [ ] Backend is running and accessible
- [ ] Frontend environment variable `NEXT_PUBLIC_API_URL` is set correctly
- [ ] CORS is configured to allow frontend origin
- [ ] API endpoints return expected response structure
- [ ] TypeScript interfaces match API responses
- [ ] Component receives correct `agentSlug` prop
- [ ] State updates are triggering re-renders
- [ ] No JavaScript errors in browser console
- [ ] Network requests are successful (check DevTools)
- [ ] Response data is not null/undefined

## Quick Test Script

Create this file to test the API directly:

**test_api_responses.js**
```javascript
const API_BASE = "http://127.0.0.1:8000";

async function testRiskAgent() {
  const response = await fetch(`${API_BASE}/api/v1/risk-decision/sample-events/`);
  const data = await response.json();
  console.log("Sample Events:", data);
  
  if (data.events && data.events.length > 0) {
    const analyzeResponse = await fetch(`${API_BASE}/api/v1/risk-decision/analyze/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data.events[0])
    });
    const decision = await analyzeResponse.json();
    console.log("Decision:", decision);
  }
}

async function testBehaviorAgent() {
  const response = await fetch(`${API_BASE}/api/v1/behavior/sample-sessions/?n=1`);
  const data = await response.json();
  console.log("Sample Sessions:", data);
  
  if (data.sessions && data.sessions.length > 0) {
    const scoreResponse = await fetch(`${API_BASE}/api/v1/behavior/score/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data.sessions[0])
    });
    const result = await scoreResponse.json();
    console.log("Behavior Result:", result);
  }
}

testRiskAgent().catch(console.error);
testBehaviorAgent().catch(console.error);
```

Run in browser console or with Node.js to verify API responses.

## Most Likely Issues

Based on the symptom "workflow working but frontend not displaying results":

1. **State not updating** - Check if `setDecision()` or `setResult()` is being called
2. **Conditional rendering failing** - Verify `agentSlug` matches expected values
3. **Response structure mismatch** - API returns different fields than frontend expects
4. **Async timing issue** - Results arrive but component doesn't re-render
5. **Error silently caught** - Check for try-catch blocks swallowing errors

## Next Steps for Other AI

1. Read `FRONTEND_DISPLAY_DEBUG_FILES.md` for context
2. Compare the files listed above between both projects
3. Identify structural differences in:
   - API response formats
   - Component state management
   - Conditional rendering logic
4. Test API endpoints directly to verify backend is working
5. Check browser console for errors
6. Add console.log statements to track data flow
7. Verify environment variables are set correctly

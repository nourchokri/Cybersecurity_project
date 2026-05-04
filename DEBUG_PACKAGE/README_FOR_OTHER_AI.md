# Instructions for Debugging Frontend Display Issue

## Quick Summary
The user has two projects:
- **project_classe-main** (WORKING) - Frontend displays results correctly
- **cybersec_project_copy** (NOT WORKING) - Backend works but frontend doesn't display results

The workflow: Data Agent → Behavior Agent → Risk Agent is working on the backend, but the frontend is not showing the results.

## What You Need to Do

### Step 1: Read the Documentation
Start by reading these files in order:
1. `COMPLETE_DEBUG_PACKAGE.md` - Complete technical reference
2. `FRONTEND_DISPLAY_DEBUG_FILES.md` - Key files overview
3. `COMPARE_PROJECTS.md` - Comparison guide

### Step 2: Understand the Architecture

**Data Flow:**
```
User clicks "Score Session" or "Run Analysis"
    ↓
Frontend calls API (lib/api.ts)
    ↓
Backend processes request (views.py)
    ↓
Backend returns JSON response
    ↓
Frontend updates state (useState)
    ↓
Component re-renders with results
    ↓
User sees results ← THIS IS FAILING
```

**Key Components:**
- `lib/api.ts` - API client (handles HTTP requests)
- `behavior-agent-live.tsx` - Displays behavior analysis results
- `risk-agent-live.tsx` - Displays risk decision results
- `app/agents/[slug]/page.tsx` - Routes to correct component

### Step 3: Identify the Problem

The issue is likely one of these:

#### A. State Not Updating
```typescript
// After API call, state should update
const result = await scoreBehaviorSession(session)
setResult(result)  // ← Is this being called?
```

#### B. Component Not Rendering
```typescript
// Component should render when result exists
{result && analysis && (
  <Card>...</Card>  // ← Is this condition true?
)}
```

#### C. API Response Format Mismatch
```typescript
// Frontend expects this structure
interface BehaviorAnomalyResult {
  event_id: string;
  user_id: string;
  flagged: boolean;
  detection_agent_analysis: {
    verdict: string;
    score: number;
    // ...
  }
}
// But backend might return different structure
```

#### D. Environment Configuration
```bash
# Frontend needs to know where backend is
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

### Step 4: Compare Projects

Use the file comparison guide in `COMPARE_PROJECTS.md` to identify differences between:
- `project_classe-main/cybersec_frontend/` (working)
- `cybersec_project_copy/` (not working)

Focus on these files:
1. `lib/api.ts` - API client
2. `components/dashboard/behavior-agent-live.tsx`
3. `components/dashboard/risk-agent-live.tsx`
4. `.env.local` or `.env`

### Step 5: Run Diagnostics

#### Test Backend Directly
```bash
# 1. Check if backend is running
curl http://127.0.0.1:8000/api/v1/behavior/health/

# 2. Get sample data
curl http://127.0.0.1:8000/api/v1/behavior/sample-sessions/?n=1

# 3. Score a session
curl -X POST http://127.0.0.1:8000/api/v1/behavior/score/ \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","hour_of_day":14,"file_count":50,"duration_minutes":60,"max_sensitivity":2,"usb_connected":0,"has_ext_email":0,"visited_exfil_domain":0,"is_outside_hours":0,"is_weekend":0,"email_count":5}'
```

#### Test Frontend API Client
Open browser console on the frontend page and run:
```javascript
// Test API connectivity
fetch('http://127.0.0.1:8000/api/v1/behavior/health/')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)
```

#### Add Debug Logging
Add these to the component:
```typescript
const handleScore = async () => {
  console.log('1. Starting score...')
  const session = sessions[selectedIdx]
  console.log('2. Session:', session)
  
  const res = await scoreBehaviorSession(session)
  console.log('3. API Response:', res)
  
  setResult(res)
  console.log('4. State updated')
}

// Track state changes
useEffect(() => {
  console.log('5. Result changed:', result)
}, [result])
```

### Step 6: Common Fixes

#### Fix 1: API Base URL
```typescript
// In lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// In .env.local
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

#### Fix 2: CORS Configuration
```python
# In Django settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

#### Fix 3: Response Structure
Compare the actual API response with the TypeScript interface:
```typescript
// If backend returns different field names, update interface
export interface BehaviorAnomalyResult {
  // Update these to match actual response
  event_id: string;
  user_id: string;
  // ...
}
```

#### Fix 4: Component Slug
```typescript
// Verify slug matches exactly
const isBehaviorAgent = agentSlug === "behavior-agent"  // case-sensitive!
```

### Step 7: Provide Solution

Once you identify the issue:
1. Explain what was wrong
2. Show the specific code that needs to change
3. Provide the corrected code
4. Explain why it wasn't working

## Key Files Reference

### Frontend (Working Version)
Located in `project_classe-main/cybersec_frontend/`:
- `lib/api.ts` - API client with all endpoints
- `components/dashboard/behavior-agent-live.tsx` - Behavior display component
- `components/dashboard/risk-agent-live.tsx` - Risk display component
- `app/agents/[slug]/page.tsx` - Agent page router
- `.env.local` - Environment configuration

### Backend (Working Version)
Located in `project_classe-main/cybersec_backend/`:
- `architecture/behavior_agent/api/views.py` - Behavior API endpoints
- `architecture/risk_decision_agent/api/views.py` - Risk API endpoints
- `config/urls.py` - URL routing configuration

## Expected Behavior

### Behavior Agent
1. User selects a session from dropdown
2. User clicks "Score Session" button
3. Frontend calls `POST /api/v1/behavior/score/`
4. Backend returns `BehaviorAnomalyResult` JSON
5. Frontend updates state with result
6. Component displays:
   - Verdict badge (LOW/MEDIUM/HIGH/CRITICAL)
   - Score and metrics
   - Dimension breakdown
   - Triggered rules
   - LLM analysis note

### Risk Agent
1. User selects an event from dropdown
2. User clicks "Run Analysis" button
3. Frontend calls `POST /api/v1/risk-decision/analyze/`
4. Backend returns `DecisionOutput` JSON
5. Frontend updates state with decision
6. Component displays:
   - Decision (ALLOW/MONITOR/ESCALATE/BLOCK)
   - Risk level (LOW/MEDIUM/HIGH)
   - Risk score
   - Analysis reasoning

## Testing Checklist

- [ ] Backend is running on port 8000
- [ ] Frontend is running on port 3000
- [ ] Environment variable `NEXT_PUBLIC_API_URL` is set
- [ ] CORS is configured correctly
- [ ] API endpoints return 200 status
- [ ] Response structure matches TypeScript interfaces
- [ ] Component receives correct `agentSlug` prop
- [ ] State updates trigger re-renders
- [ ] No errors in browser console
- [ ] No errors in backend logs

## Questions to Ask User

If you need more information:
1. "Can you open the browser console and share any error messages?"
2. "Can you check the Network tab and share the API response for the failing request?"
3. "Is the backend running? Can you access http://127.0.0.1:8000/api/v1/behavior/health/ in your browser?"
4. "What is the value of `NEXT_PUBLIC_API_URL` in your .env file?"
5. "Can you add `console.log(result)` after the API call and share what it prints?"

## Success Criteria

The issue is fixed when:
1. User clicks "Score Session" or "Run Analysis"
2. Loading spinner appears
3. API call completes successfully
4. Results appear in the UI with:
   - Decision/verdict badge
   - Scores and metrics
   - Analysis details
   - No errors in console

## Additional Resources

All technical details are in:
- `COMPLETE_DEBUG_PACKAGE.md` - Full technical reference
- `FRONTEND_DISPLAY_DEBUG_FILES.md` - File descriptions
- `COMPARE_PROJECTS.md` - Comparison guide

Good luck! The working version is in `project_classe-main`, so you have a complete reference to compare against.

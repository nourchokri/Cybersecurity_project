# Quick Start Debug Guide

## Problem
Frontend not displaying results from Behavior Agent → Risk Agent workflow (backend works fine)

## Files to Give Another AI

### Documentation (Read First)
1. ✅ `README_FOR_OTHER_AI.md` - Start here
2. ✅ `COMPLETE_DEBUG_PACKAGE.md` - Full technical details
3. ✅ `FRONTEND_DISPLAY_DEBUG_FILES.md` - Key files overview
4. ✅ `COMPARE_PROJECTS.md` - Comparison guide

### Working Frontend Files (from project_classe-main)
```
cybersec_frontend/
├── lib/api.ts                                    ← API client
├── components/dashboard/
│   ├── behavior-agent-live.tsx                   ← Behavior display
│   └── risk-agent-live.tsx                       ← Risk display
├── app/agents/[slug]/page.tsx                    ← Router
└── .env.local                                    ← Config
```

### Working Backend Files (from project_classe-main)
```
cybersec_backend/
├── architecture/
│   ├── behavior_agent/api/views.py               ← Behavior endpoints
│   └── risk_decision_agent/api/views.py          ← Risk endpoints
└── config/urls.py                                ← URL routing
```

## 5-Minute Diagnostic

### 1. Test Backend (30 seconds)
```bash
curl http://127.0.0.1:8000/api/v1/behavior/health/
# Expected: {"status":"ok","agent":"behavior_agent","version":"1.0.0"}
```

### 2. Test Frontend API (30 seconds)
Open browser console on frontend page:
```javascript
fetch('http://127.0.0.1:8000/api/v1/behavior/health/')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)
// Expected: Same as above
// If error: CORS or API_BASE_URL issue
```

### 3. Check Environment (30 seconds)
```bash
# In cybersec_project_copy/.env or .env.local
cat .env.local | grep NEXT_PUBLIC_API_URL
# Expected: NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

### 4. Test Full Flow (2 minutes)
```bash
# Get sample session
curl http://127.0.0.1:8000/api/v1/behavior/sample-sessions/?n=1

# Score it (copy session data from above)
curl -X POST http://127.0.0.1:8000/api/v1/behavior/score/ \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","hour_of_day":14,"file_count":50,"duration_minutes":60,"max_sensitivity":2,"usb_connected":0,"has_ext_email":0,"visited_exfil_domain":0,"is_outside_hours":0,"is_weekend":0,"email_count":5}'

# Expected: Full BehaviorAnomalyResult JSON
```

### 5. Check Browser Console (1 minute)
1. Open DevTools (F12)
2. Go to Console tab
3. Look for errors (red text)
4. Go to Network tab
5. Click "Score Session" button
6. Check the API request/response

## Most Likely Issues

### Issue 1: Environment Variable Not Set (60% probability)
**Symptom:** Network errors, "Failed to fetch"
**Fix:**
```bash
# Create or edit .env.local in frontend root
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000" > .env.local
# Restart frontend: npm run dev
```

### Issue 2: State Not Updating (20% probability)
**Symptom:** No errors, but UI doesn't update
**Fix:** Add debug logging in component:
```typescript
const handleScore = async () => {
  const res = await scoreBehaviorSession(session)
  console.log('API Response:', res)  // ← Add this
  setResult(res)
}
```

### Issue 3: Response Structure Mismatch (10% probability)
**Symptom:** TypeScript errors or undefined properties
**Fix:** Compare API response with TypeScript interface in `lib/api.ts`

### Issue 4: Component Not Rendering (5% probability)
**Symptom:** Blank screen
**Fix:** Check `agentSlug` matches "behavior-agent" or "risk-behavior-agent"

### Issue 5: CORS (5% probability)
**Symptom:** CORS error in console
**Fix:** Add to Django settings:
```python
CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
```

## Quick Fixes

### Fix 1: Copy Working Files
```bash
# Copy working API client
cp project_classe-main/cybersec_frontend/lib/api.ts \
   cybersec_project_copy/lib/api.ts

# Copy working components
cp project_classe-main/cybersec_frontend/components/dashboard/behavior-agent-live.tsx \
   cybersec_project_copy/components/dashboard/behavior-agent-live.tsx

cp project_classe-main/cybersec_frontend/components/dashboard/risk-agent-live.tsx \
   cybersec_project_copy/components/dashboard/risk-agent-live.tsx
```

### Fix 2: Set Environment Variable
```bash
cd cybersec_project_copy
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000" > .env.local
npm run dev  # Restart frontend
```

### Fix 3: Add Debug Logging
```typescript
// In behavior-agent-live.tsx or risk-agent-live.tsx
const handleScore = async () => {
  console.log('1. Starting...')
  const session = sessions[selectedIdx]
  console.log('2. Session:', session)
  
  try {
    const res = await scoreBehaviorSession(session)
    console.log('3. Response:', res)
    setResult(res)
    console.log('4. State updated')
  } catch (error) {
    console.error('5. Error:', error)
  }
}
```

## Key API Endpoints

### Behavior Agent
- `GET /api/v1/behavior/health/` - Health check
- `GET /api/v1/behavior/sample-sessions/?n=30&flagged=1` - Get test data
- `POST /api/v1/behavior/score/` - Score a session

### Risk Agent
- `GET /api/v1/risk-decision/health/` - Health check
- `GET /api/v1/risk-decision/sample-events/` - Get test data
- `POST /api/v1/risk-decision/analyze/` - Analyze an event

## Expected Response Formats

### Behavior Agent Response
```json
{
  "event_id": "evt_123",
  "user_id": "user_456",
  "flagged": true,
  "if_score": 0.82,
  "combined_score": 0.85,
  "detection_agent_analysis": {
    "verdict": "HIGH",
    "score": 0.82,
    "analyst_note": "Suspicious activity...",
    "dimension_breakdown": {
      "time": 0.75,
      "device": 0.90,
      "volume": 0.60,
      "sensitivity": 0.80
    }
  }
}
```

### Risk Agent Response
```json
{
  "event_id": "evt_123",
  "user_id": "user_456",
  "decision": "ESCALATE",
  "risk_level": "HIGH",
  "adjusted_risk_score": 0.95,
  "decision_reasoning": "Multiple high-risk factors..."
}
```

## Success Checklist

- [ ] Backend returns 200 status
- [ ] Response structure matches TypeScript interface
- [ ] `NEXT_PUBLIC_API_URL` is set correctly
- [ ] No CORS errors in console
- [ ] State updates after API call
- [ ] Component renders with results
- [ ] User sees decision/verdict badge
- [ ] User sees scores and metrics

## If Still Stuck

1. Share browser console errors
2. Share Network tab response
3. Share `console.log(result)` output
4. Compare with working version in `project_classe-main`

## File Locations

### Working Project
```
project_classe-main/
└── cybersec_frontend/          ← Working frontend
    └── cybersec_backend/       ← Working backend
```

### Broken Project
```
cybersec_project_copy/          ← Not working (needs fix)
```

## Next Steps

1. Read `README_FOR_OTHER_AI.md`
2. Run 5-minute diagnostic above
3. Try quick fixes
4. Compare files with working version
5. Add debug logging if needed
6. Check `COMPLETE_DEBUG_PACKAGE.md` for details

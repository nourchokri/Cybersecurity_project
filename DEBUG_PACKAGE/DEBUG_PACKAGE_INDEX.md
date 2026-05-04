# Debug Package Index

## Overview
This package contains all the files needed to debug the frontend display issue where the Behavior Agent → Risk Agent workflow works on the backend but results are not displayed in the frontend.

## 📋 Documentation Files (Read in This Order)

### 1. START HERE: Quick Start
**File:** `QUICK_START_DEBUG.md`
- 5-minute diagnostic guide
- Most common issues and fixes
- Quick commands to test the system
- **Read this first for immediate action**

### 2. Instructions for Another AI
**File:** `README_FOR_OTHER_AI.md`
- Step-by-step debugging instructions
- What to look for
- How to identify the problem
- Questions to ask the user
- **Read this second for context**

### 3. Complete Technical Reference
**File:** `COMPLETE_DEBUG_PACKAGE.md`
- Full architecture overview
- Complete API documentation
- Response format specifications
- Testing procedures
- **Read this for deep technical details**

### 4. Key Files Overview
**File:** `FRONTEND_DISPLAY_DEBUG_FILES.md`
- List of all important files
- What each file does
- Where to find them
- **Use this as a reference**

### 5. Project Comparison Guide
**File:** `COMPARE_PROJECTS.md`
- Files to compare between projects
- What differences to look for
- Debugging checklist
- **Use this to identify differences**

## 🗂️ Working Code Reference

### Frontend Files (Working Version)
Located in: `project_classe-main/cybersec_frontend/`

**Core Files:**
- `lib/api.ts` - API client with all endpoints and type definitions
- `components/dashboard/behavior-agent-live.tsx` - Behavior analysis display
- `components/dashboard/risk-agent-live.tsx` - Risk decision display
- `app/agents/[slug]/page.tsx` - Agent page router
- `.env.local` - Environment configuration

### Backend Files (Working Version)
Located in: `project_classe-main/cybersec_backend/`

**Core Files:**
- `architecture/behavior_agent/api/views.py` - Behavior API endpoints
- `architecture/risk_decision_agent/api/views.py` - Risk API endpoints
- `config/urls.py` - URL routing configuration

## 🎯 Quick Reference

### Problem Statement
- **Working:** `project_classe-main` - Frontend displays results correctly
- **Not Working:** `cybersec_project_copy` - Backend works but frontend doesn't display results

### Data Flow
```
User Action (Click Button)
    ↓
Frontend Component (behavior-agent-live.tsx or risk-agent-live.tsx)
    ↓
API Client (lib/api.ts)
    ↓
HTTP Request to Backend
    ↓
Backend API (views.py)
    ↓
Backend Processing
    ↓
JSON Response
    ↓
API Client Receives Response
    ↓
Component State Updates (useState)
    ↓
Component Re-renders
    ↓
User Sees Results ← THIS IS FAILING
```

### Key API Endpoints

**Behavior Agent:**
- `POST /api/v1/behavior/score/` - Score a session
- `GET /api/v1/behavior/sample-sessions/` - Get test data

**Risk Agent:**
- `POST /api/v1/risk-decision/analyze/` - Analyze an event
- `GET /api/v1/risk-decision/sample-events/` - Get test data

### Most Common Issues (in order of probability)

1. **Environment Variable Not Set (60%)** - `NEXT_PUBLIC_API_URL` missing
2. **State Not Updating (20%)** - `setResult()` not called or not triggering re-render
3. **Response Structure Mismatch (10%)** - Backend returns different fields than expected
4. **Component Not Rendering (5%)** - Conditional rendering logic failing
5. **CORS Issues (5%)** - Backend not allowing frontend origin

## 🔧 Quick Diagnostic Commands

### Test Backend
```bash
curl http://127.0.0.1:8000/api/v1/behavior/health/
```

### Test Frontend API
```javascript
// Run in browser console
fetch('http://127.0.0.1:8000/api/v1/behavior/health/')
  .then(r => r.json())
  .then(console.log)
```

### Check Environment
```bash
cat cybersec_project_copy/.env.local | grep NEXT_PUBLIC_API_URL
```

## 📊 File Structure

```
project_classe-main/
├── DEBUG_PACKAGE_INDEX.md              ← You are here
├── QUICK_START_DEBUG.md                ← Start here
├── README_FOR_OTHER_AI.md              ← Instructions
├── COMPLETE_DEBUG_PACKAGE.md           ← Full reference
├── FRONTEND_DISPLAY_DEBUG_FILES.md     ← File overview
├── COMPARE_PROJECTS.md                 ← Comparison guide
│
├── cybersec_frontend/                  ← Working frontend
│   ├── lib/api.ts
│   ├── components/dashboard/
│   │   ├── behavior-agent-live.tsx
│   │   └── risk-agent-live.tsx
│   └── app/agents/[slug]/page.tsx
│
└── cybersec_backend/                   ← Working backend
    ├── architecture/
    │   ├── behavior_agent/api/views.py
    │   └── risk_decision_agent/api/views.py
    └── config/urls.py
```

## 🚀 Getting Started

### For Quick Fix (5 minutes)
1. Read `QUICK_START_DEBUG.md`
2. Run the 5-minute diagnostic
3. Try the quick fixes

### For Thorough Investigation (30 minutes)
1. Read `README_FOR_OTHER_AI.md`
2. Read `COMPLETE_DEBUG_PACKAGE.md`
3. Compare files using `COMPARE_PROJECTS.md`
4. Run full diagnostic tests
5. Add debug logging
6. Identify and fix the issue

### For Another AI to Debug
Give them these files in order:
1. `DEBUG_PACKAGE_INDEX.md` (this file)
2. `README_FOR_OTHER_AI.md`
3. `COMPLETE_DEBUG_PACKAGE.md`
4. Access to both project directories for comparison

## 📝 Key Concepts

### TypeScript Interfaces
The frontend expects specific response structures defined in `lib/api.ts`:
- `BehaviorAnomalyResult` - Response from behavior scoring
- `DecisionOutput` - Response from risk analysis
- `SessionInput` - Input for behavior scoring
- `AnomalyEvent` - Input for risk analysis

### Component State Management
Components use React hooks:
- `useState` - Stores API response data
- `useEffect` - Loads initial data and tracks changes
- `useCallback` - Optimizes callback functions

### Conditional Rendering
Components only display results when data exists:
```typescript
{result && analysis && (
  <Card>
    {/* Display results */}
  </Card>
)}
```

## 🔍 Debugging Strategy

### Step 1: Verify Backend
- Backend is running
- Endpoints return 200 status
- Response structure is correct

### Step 2: Verify Frontend Configuration
- Environment variables are set
- API base URL is correct
- CORS is configured

### Step 3: Verify API Client
- API calls are being made
- Responses are received
- No network errors

### Step 4: Verify Component State
- State is being updated
- State updates trigger re-renders
- Data is not null/undefined

### Step 5: Verify Component Rendering
- Conditional rendering logic is correct
- Component receives correct props
- No JavaScript errors

## 📞 Support

If you need more information:
- Check browser console for errors
- Check Network tab for API responses
- Add `console.log()` statements to track data flow
- Compare with working version in `project_classe-main`

## ✅ Success Criteria

The issue is fixed when:
1. User clicks "Score Session" or "Run Analysis"
2. Loading spinner appears
3. API call completes (check Network tab)
4. Results appear in UI:
   - Decision/verdict badge visible
   - Scores and metrics displayed
   - Analysis details shown
5. No errors in console

## 📚 Additional Resources

All working code is in `project_classe-main/`:
- Frontend: `cybersec_frontend/`
- Backend: `cybersec_backend/`

Compare with non-working code in `cybersec_project_copy/`

## 🎓 Learning Points

This issue demonstrates:
- Frontend-backend integration
- React state management
- TypeScript type safety
- API client design
- Error handling
- Debugging techniques

## 📌 Notes

- The backend is confirmed working (workflow executes correctly)
- The issue is specifically in the frontend display layer
- The working version exists in `project_classe-main` for reference
- All necessary files are included in this package

---

**Last Updated:** 2026-05-02
**Version:** 1.0
**Status:** Ready for debugging

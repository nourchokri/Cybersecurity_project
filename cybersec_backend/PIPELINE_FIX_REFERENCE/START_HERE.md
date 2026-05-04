# 🚀 Pipeline Fix Reference - START HERE

## 📁 What is This Folder?

This folder contains **working reference files** from the `project_classe-main` version that successfully implements the full pipeline flow from Data Agent to Behavior Agent.

Use these files to fix the broken pipeline in `aa-main`.

---

## 🎯 The Problem

In `aa-main`, when you click **"Start Pipeline with Real Data"**:
- ✅ Events are collected
- ❌ Events are NOT forwarded to Behavior Agent
- ❌ No behavioral analysis happens

---

## 📚 Files in This Folder

### **📖 Documentation**
- **`START_HERE.md`** ← You are here
- **`README.md`** - Detailed problem description and architecture
- **`INSTRUCTIONS_FOR_AI.md`** - Step-by-step fix instructions

### **💻 Reference Code**
- **`api/views.py`** - Pipeline endpoint (`PipelineCollectView`)
- **`api/urls.py`** - URL routing with pipeline endpoint
- **`application/data_service.py`** - Main orchestration logic
- **`application/session_aggregator.py`** - Event-to-session conversion
- **`integrations/behavior_agent_client.py`** - HTTP client for Behavior Agent
- **`infrastructure/mcp_integration_EXCERPT.py`** - Event tracking example
- **`behavior_agent/api/views_EXCERPT.py`** - Receiving side reference

---

## 🔧 Quick Start Guide

### **Step 1: Read the Instructions**
Open **`INSTRUCTIONS_FOR_AI.md`** and follow the step-by-step guide.

### **Step 2: Identify Missing Components**
Check if `aa-main` has:
- [ ] Pipeline endpoint (`/api/v1/data/pipeline-collect/`)
- [ ] Event tracking in collection results
- [ ] Session aggregator class
- [ ] Behavior Agent HTTP client
- [ ] Pipeline orchestration method

### **Step 3: Copy Reference Files**
Copy these files to `aa-main` (adjust paths as needed):
1. `application/session_aggregator.py`
2. `integrations/behavior_agent_client.py`

### **Step 4: Modify Existing Files**
Update these files in `aa-main`:
1. `api/views.py` - Add `PipelineCollectView`
2. `api/urls.py` - Add pipeline route
3. `application/data_service.py` - Add `collect_and_forward_to_behavior()`
4. `infrastructure/mcp_integration.py` - Track `collected_events`

### **Step 5: Test**
1. Start backend: `python manage.py runserver`
2. Click "Start Pipeline with Real Data"
3. Verify logs show: "Pipeline complete: X events → Y sessions → Behavior Agent (Z flagged)"

---

## 🎓 Understanding the Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User clicks "Start Pipeline with Real Data"             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Frontend: POST /api/v1/data/pipeline-collect/           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. PipelineCollectView.post()                              │
│    └─ Calls: data_service.collect_and_forward_to_behavior()│
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. collect_and_forward_to_behavior()                       │
│    ├─ Step 1: collect_events() → {collected_events: [...]} │
│    ├─ Step 2: _extract_events_from_collection()            │
│    ├─ Step 3: session_aggregator.aggregate_events_to_sessions()│
│    └─ Step 4: behavior_client.send_sessions()              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. HTTP POST to Behavior Agent                             │
│    URL: http://127.0.0.1:8000/api/v1/behavior/batch/       │
│    Payload: {sessions: [...]}                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Behavior Agent analyzes sessions                        │
│    Returns: {results: [{anomaly_result: {...}}]}           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Frontend displays: "3 sessions analyzed, 1 flagged"     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔑 Key Components

### **1. Pipeline Endpoint**
**File:** `api/views.py`
**Purpose:** Entry point for pipeline requests
**Key Code:** `PipelineCollectView` class

### **2. Event Tracking**
**File:** `infrastructure/mcp_integration.py`
**Purpose:** Store events in a list during collection
**Key Code:** `all_collected_events.extend(events_list)`

### **3. Session Aggregation**
**File:** `application/session_aggregator.py`
**Purpose:** Convert events to session format
**Key Code:** `aggregate_events_to_sessions()` method

### **4. HTTP Client**
**File:** `integrations/behavior_agent_client.py`
**Purpose:** Send sessions to Behavior Agent
**Key Code:** `send_sessions()` method

### **5. Orchestration**
**File:** `application/data_service.py`
**Purpose:** Tie everything together
**Key Code:** `collect_and_forward_to_behavior()` method

---

## ⚠️ Common Mistakes to Avoid

1. **Don't just copy event counts** - You need the actual event objects
2. **Don't skip session aggregation** - Behavior Agent expects SessionInput format
3. **Don't forget to install httpx** - Required for HTTP client
4. **Don't use wrong URL** - Behavior Agent is at `http://127.0.0.1:8000`
5. **Don't forget to add the route** - Pipeline endpoint must be in urls.py

---

## 📊 Expected Result

After the fix, the response should look like:

```json
{
  "ok": true,
  "llm_reasoning": "Collected events from system, network, file collectors",
  "tools_executed": ["collect_system_events", "collect_network_events", ...],
  "events_by_tool": {
    "collect_system_events": 50,
    "collect_network_events": 30,
    ...
  },
  "total_events": 150,
  "collected_events": [...],  // ← Actual event objects
  "sessions_created": 3,
  "behavior_result": {
    "ok": true,
    "sessions_sent": 3,
    "flagged_count": 1,
    "skipped_count": 0,
    "results": [
      {
        "ok": true,
        "anomaly_result": {
          "user_id": "AAA0001",
          "flagged": true,
          "combined_score": 0.85,
          ...
        }
      },
      ...
    ]
  },
  "timestamp": "2026-05-02T10:30:00",
  "status": "success"
}
```

---

## 🆘 Need Help?

1. **Read `INSTRUCTIONS_FOR_AI.md`** - Detailed step-by-step guide
2. **Check `README.md`** - Architecture and design explanation
3. **Compare with reference files** - See working implementation
4. **Check logs** - Look for error messages in console

---

## ✅ Success Checklist

- [ ] Pipeline endpoint responds (no 404)
- [ ] Events are collected (total_events > 0)
- [ ] Events are tracked (collected_events is not empty)
- [ ] Sessions are created (sessions_created > 0)
- [ ] Sessions are sent (behavior_result.ok = true)
- [ ] Behavior Agent analyzes (behavior_result.results not empty)
- [ ] Frontend shows results (flagged count displayed)

---

## 🎯 Next Steps

1. Open **`INSTRUCTIONS_FOR_AI.md`**
2. Follow the 6-step implementation guide
3. Test the pipeline
4. Verify all checklist items pass

Good luck! 🚀

---

**Questions?** Check the reference files in this folder for working examples.

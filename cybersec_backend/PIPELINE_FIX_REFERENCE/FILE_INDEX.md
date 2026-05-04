# 📁 Pipeline Fix Reference - File Index

## 📂 Folder Structure

```
PIPELINE_FIX_REFERENCE/
├── 📄 START_HERE.md                          ← Read this first!
├── 📄 GIVE_THIS_TO_AI.txt                    ← Quick prompt for AI
├── 📄 INSTRUCTIONS_FOR_AI.md                 ← Step-by-step fix guide
├── 📄 README.md                              ← Problem description
├── 📄 FILE_INDEX.md                          ← This file
│
├── 📁 api/
│   ├── views.py                              ← Pipeline endpoint
│   └── urls.py                               ← URL routing
│
├── 📁 application/
│   ├── data_service.py                       ← Main orchestration
│   └── session_aggregator.py                 ← Event-to-session conversion
│
├── 📁 integrations/
│   └── behavior_agent_client.py              ← HTTP client for Behavior Agent
│
├── 📁 infrastructure/
│   └── mcp_integration_EXCERPT.py            ← Event tracking example
│
└── 📁 behavior_agent/
    └── api/
        └── views_EXCERPT.py                  ← Receiving side reference
```

---

## 📖 Documentation Files

### **START_HERE.md**
- **Purpose:** Entry point for the fix
- **Contains:** Quick start guide, overview, success checklist
- **Read:** First

### **GIVE_THIS_TO_AI.txt**
- **Purpose:** Quick prompt to give to another AI
- **Contains:** Problem statement, task description
- **Read:** If you need a quick summary

### **INSTRUCTIONS_FOR_AI.md**
- **Purpose:** Detailed implementation guide
- **Contains:** 6-step fix process, code examples, troubleshooting
- **Read:** Second (after START_HERE.md)

### **README.md**
- **Purpose:** Comprehensive problem description
- **Contains:** Architecture, data flow, expected results
- **Read:** For deep understanding

### **FILE_INDEX.md**
- **Purpose:** This file - navigation guide
- **Contains:** File structure and descriptions
- **Read:** For reference

---

## 💻 Code Reference Files

### **api/views.py**
- **Purpose:** API endpoint for pipeline
- **Key Class:** `PipelineCollectView`
- **Key Method:** `post()` - handles pipeline requests
- **Lines to Focus:** 120-150 (PipelineCollectView)
- **Copy to:** `aa-main/api/views.py` (or equivalent)

### **api/urls.py**
- **Purpose:** URL routing configuration
- **Key Route:** `path('pipeline-collect/', ...)`
- **Lines to Focus:** 11 (pipeline route)
- **Copy to:** `aa-main/api/urls.py` (or equivalent)

### **application/data_service.py**
- **Purpose:** Main pipeline orchestration logic
- **Key Method:** `collect_and_forward_to_behavior()` - orchestrates entire pipeline
- **Helper Method:** `_extract_events_from_collection()` - extracts events
- **Lines to Focus:** 40-125 (pipeline methods)
- **Copy to:** `aa-main/application/data_service.py` (or equivalent)

### **application/session_aggregator.py**
- **Purpose:** Converts events to session format
- **Key Class:** `SessionAggregator`
- **Key Method:** `aggregate_events_to_sessions()` - main conversion logic
- **Lines to Focus:** 60-120 (aggregation logic)
- **Copy to:** `aa-main/application/session_aggregator.py` (create new file)

### **integrations/behavior_agent_client.py**
- **Purpose:** HTTP client for Behavior Agent communication
- **Key Class:** `BehaviorAgentClient`
- **Key Method:** `send_sessions()` - sends sessions via HTTP POST
- **Lines to Focus:** 30-120 (send_sessions method)
- **Copy to:** `aa-main/integrations/behavior_agent_client.py` (create new file)
- **Dependencies:** Requires `httpx` library (`pip install httpx`)

### **infrastructure/mcp_integration_EXCERPT.py**
- **Purpose:** Example of event tracking in collection
- **Key Concept:** `all_collected_events` list accumulation
- **Lines to Focus:** 15-45 (event tracking logic)
- **Reference for:** Modifying your existing MCP integration

### **behavior_agent/api/views_EXCERPT.py**
- **Purpose:** Shows how Behavior Agent receives sessions
- **Key Class:** `BatchScoreView`
- **Key Method:** `post()` - receives and processes sessions
- **Lines to Focus:** 15-50 (batch processing)
- **Reference for:** Understanding the receiving side

---

## 🎯 Implementation Order

1. **Read Documentation**
   - START_HERE.md
   - INSTRUCTIONS_FOR_AI.md

2. **Copy New Files**
   - application/session_aggregator.py
   - integrations/behavior_agent_client.py

3. **Modify Existing Files**
   - api/views.py (add PipelineCollectView)
   - api/urls.py (add pipeline route)
   - application/data_service.py (add pipeline methods)
   - infrastructure/mcp_integration.py (add event tracking)

4. **Install Dependencies**
   - `pip install httpx`

5. **Test**
   - Start backend
   - Click "Start Pipeline"
   - Verify logs and response

---

## 🔍 Quick Reference

### **Where to Find:**

| What You Need | File | Method/Class |
|---------------|------|--------------|
| Pipeline endpoint | api/views.py | PipelineCollectView |
| URL routing | api/urls.py | urlpatterns |
| Main orchestration | application/data_service.py | collect_and_forward_to_behavior() |
| Event extraction | application/data_service.py | _extract_events_from_collection() |
| Session conversion | application/session_aggregator.py | aggregate_events_to_sessions() |
| HTTP client | integrations/behavior_agent_client.py | send_sessions() |
| Event tracking | infrastructure/mcp_integration_EXCERPT.py | all_collected_events |

---

## 📊 File Dependencies

```
PipelineCollectView (api/views.py)
    └─ calls: data_service.collect_and_forward_to_behavior()
        │
        ├─ calls: data_service.collect_events()
        │   └─ returns: {collected_events: [...]}
        │
        ├─ calls: data_service._extract_events_from_collection()
        │   └─ returns: [event1, event2, ...]
        │
        ├─ calls: session_aggregator.aggregate_events_to_sessions()
        │   └─ returns: [session1, session2, ...]
        │
        └─ calls: behavior_client.send_sessions()
            └─ HTTP POST to Behavior Agent
                └─ returns: {ok, sessions_sent, flagged_count, results}
```

---

## ✅ Checklist

Use this to track your progress:

- [ ] Read START_HERE.md
- [ ] Read INSTRUCTIONS_FOR_AI.md
- [ ] Copy session_aggregator.py
- [ ] Copy behavior_agent_client.py
- [ ] Add PipelineCollectView to views.py
- [ ] Add pipeline route to urls.py
- [ ] Add collect_and_forward_to_behavior() to data_service.py
- [ ] Add _extract_events_from_collection() to data_service.py
- [ ] Add event tracking to mcp_integration.py
- [ ] Install httpx
- [ ] Test pipeline
- [ ] Verify logs
- [ ] Verify response

---

## 🆘 Troubleshooting

| Issue | Check File | Look For |
|-------|-----------|----------|
| 404 on pipeline endpoint | api/urls.py | pipeline-collect route |
| No events collected | infrastructure/mcp_integration.py | all_collected_events |
| No sessions created | application/session_aggregator.py | aggregate_events_to_sessions() |
| Connection refused | integrations/behavior_agent_client.py | base_url |
| Module not found | Terminal | pip install httpx |

---

**Ready to start?** Open **START_HERE.md** now! 🚀

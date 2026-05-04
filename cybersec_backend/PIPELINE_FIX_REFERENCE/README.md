# Pipeline Fix Reference - Working Version Files

## 🎯 Problem Description

**Issue:** In aa-main, when clicking "Start Pipeline with Real Data", events are collected but NOT forwarded to the behavior agent for analysis.

**Root Cause:** The aa-main version is missing the pipeline orchestration logic that:
1. Collects events from collectors
2. Extracts events from collection results
3. Aggregates events into sessions
4. Sends sessions to Behavior Agent via HTTP (A2A communication)

---

## 📁 Files in This Reference Folder

This folder contains the **WORKING** implementation from `project_classe-main` that successfully implements the full pipeline flow.

### **Core Pipeline Files:**

1. **`api/views.py`** - API endpoints including `PipelineCollectView`
2. **`application/data_service.py`** - Main orchestration with `collect_and_forward_to_behavior()`
3. **`application/session_aggregator.py`** - Converts events to sessions
4. **`integrations/behavior_agent_client.py`** - A2A HTTP client for Behavior Agent
5. **`infrastructure/mcp_integration.py`** - Event collection with tracking
6. **`api/urls.py`** - URL routing

### **Reference Files:**

7. **`behavior_agent/api/views.py`** - Shows how Behavior Agent receives sessions

---

## 🔧 How to Fix aa-main

### **Step 1: Understand the Flow**

```
User clicks "Start Pipeline"
    ↓
Frontend calls: POST /api/v1/data/pipeline-collect/
    ↓
PipelineCollectView.post() [views.py]
    ↓
data_service.collect_and_forward_to_behavior() [data_service.py]
    ↓
├─ Step 1: collect_events() - Collect from MCP collectors
├─ Step 2: _extract_events_from_collection() - Extract event list
├─ Step 3: session_aggregator.aggregate_events_to_sessions() - Create sessions
└─ Step 4: behavior_client.send_sessions() - HTTP POST to Behavior Agent
    ↓
Behavior Agent receives at: POST /api/v1/behavior/batch/
```

### **Step 2: Key Code Sections to Implement**

#### **A. Pipeline Endpoint (views.py lines 130-150)**
```python
class PipelineCollectView(APIView):
    def post(self, request):
        # Validate request
        # Call data_service.collect_and_forward_to_behavior()
        # Return result
```

#### **B. Pipeline Orchestration (data_service.py lines 40-125)**
```python
def collect_and_forward_to_behavior(self, collectors):
    # 1. Collect events
    collection_result = self.collect_events(collectors)
    
    # 2. Extract events
    all_events = self._extract_events_from_collection(collection_result)
    
    # 3. Aggregate to sessions
    sessions = self.session_aggregator.aggregate_events_to_sessions(all_events)
    
    # 4. Send to Behavior Agent
    behavior_result = self.behavior_client.send_sessions(sessions, pipeline_mode=True)
    
    return {**collection_result, 'behavior_result': behavior_result}
```

#### **C. Event Tracking (mcp_integration.py line 387)**
```python
# In run_agent_iteration(), accumulate events:
all_collected_events = []  # Track across iterations
# ... when tool executes ...
if events_list:
    all_collected_events.extend(events_list)
# ... at end ...
return {'collected_events': all_collected_events, ...}
```

#### **D. Session Aggregation (session_aggregator.py)**
```python
def aggregate_events_to_sessions(self, events):
    # Group by user_id
    # Calculate session metrics (file_count, email_count, etc.)
    # Return list of SessionInput dicts
```

#### **E. Behavior Agent Client (behavior_agent_client.py)**
```python
def send_sessions(self, sessions, pipeline_mode=False):
    # POST to http://127.0.0.1:8000/api/v1/behavior/batch/
    # Return {ok, sessions_sent, flagged_count, results}
```

### **Step 3: Implementation Checklist**

- [ ] Add `PipelineCollectView` to API views
- [ ] Add `pipeline-collect/` route to urls.py
- [ ] Implement `collect_and_forward_to_behavior()` in data service
- [ ] Implement `_extract_events_from_collection()` helper
- [ ] Create `SessionAggregator` class
- [ ] Create `BehaviorAgentClient` class
- [ ] Modify event collection to track `collected_events` list
- [ ] Update `collect_events()` to return `collected_events` in result
- [ ] Test the full pipeline flow

---

## 🔍 Key Differences Between Working and Broken Versions

### **Working Version (project_classe-main):**
✅ Has dedicated pipeline endpoint
✅ Tracks collected events in a list
✅ Extracts events from collection results
✅ Aggregates events into sessions
✅ Sends sessions via HTTP to Behavior Agent
✅ Returns complete pipeline result with behavior analysis

### **Broken Version (aa-main):**
❌ Missing pipeline endpoint or incomplete implementation
❌ Events collected but not tracked/extracted
❌ No session aggregation logic
❌ No HTTP client for Behavior Agent communication
❌ Pipeline stops after collection, never forwards

---

## 📊 Expected Result After Fix

When "Start Pipeline with Real Data" is clicked:

```json
{
  "ok": true,
  "llm_reasoning": "Collected events from system, network, file collectors",
  "tools_executed": ["collect_system_events", "collect_network_events", ...],
  "total_events": 150,
  "sessions_created": 3,
  "behavior_result": {
    "ok": true,
    "sessions_sent": 3,
    "flagged_count": 1,
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
  }
}
```

---

## 🚀 Testing the Fix

1. **Start both agents:**
   ```bash
   # Terminal 1: Start Django backend
   python manage.py runserver
   ```

2. **Open frontend and click "Start Pipeline with Real Data"**

3. **Verify in logs:**
   ```
   [data_agent] Pipeline mode: Collecting events and forwarding to Behavior Agent
   [data_agent] Extracted 150 events from collection
   [data_agent] Aggregated 150 events into 3 sessions
   [data_agent] Sending 3 session(s) to Behavior Agent (pipeline_mode=True)
   [behavior_agent] Received 3 sessions for batch analysis
   [data_agent] Pipeline complete: 150 events → 3 sessions → Behavior Agent (1 flagged)
   ```

4. **Check response includes `behavior_result`**

---

## 📞 Need Help?

Compare your aa-main implementation with these reference files line-by-line. The key is ensuring:
1. Events are tracked in a list during collection
2. Events are extracted and passed to session aggregator
3. Sessions are sent via HTTP to Behavior Agent
4. Results are returned to frontend

Good luck! 🎉

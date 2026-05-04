# Instructions for Fixing the Pipeline in aa-main

## 🎯 Problem Statement

The aa-main version has a broken pipeline where:
- ✅ Events are collected successfully
- ❌ Events are NOT forwarded to the Behavior Agent
- ❌ No behavioral analysis happens
- ❌ Pipeline stops after collection

## 📋 What You Have

You have access to:
1. **aa-main codebase** - The broken version that needs fixing
2. **This reference folder** - Working implementation from project_classe-main

## 🔍 Root Cause Analysis

The aa-main version is missing:
1. **Pipeline endpoint** - No dedicated endpoint for pipeline mode
2. **Event tracking** - Events collected but not stored in result
3. **Session aggregation** - No logic to convert events to sessions
4. **Behavior client** - No HTTP client to send data to Behavior Agent
5. **Pipeline orchestration** - No method that ties everything together

## 🛠️ Step-by-Step Fix

### **Step 1: Add Pipeline Endpoint**

**File:** `api/views.py` (or equivalent in aa-main)

Add this view class:

```python
class PipelineCollectView(APIView):
    """POST /api/v1/data/pipeline-collect/"""
    
    def post(self, request):
        serializer = CollectRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': 'Invalid request'}, status=400)
        
        try:
            service = get_data_service()
            collectors = serializer.validated_data.get('collectors', [])
            result = service.collect_and_forward_to_behavior(collectors)
            return Response(result, status=200)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
```

**File:** `api/urls.py` (or equivalent)

Add this route:

```python
path('pipeline-collect/', views.PipelineCollectView.as_view(), name='pipeline-collect'),
```

---

### **Step 2: Track Collected Events**

**File:** `infrastructure/mcp_integration.py` (or equivalent)

In your event collection method, track events in a list:

```python
def run_agent_iteration(self, collectors):
    all_collected_events = []  # ← Add this
    events_by_tool = {}
    
    for tool_call in tool_calls:
        result = execute_tool(tool_call)
        
        # Extract events from result
        if isinstance(result, dict) and 'events' in result:
            events_list = result['events']
            if isinstance(events_list, list):
                all_collected_events.extend(events_list)  # ← Add this
                events_by_tool[tool_name] = len(events_list)
    
    return {
        'ok': True,
        'tools_executed': tools_executed,
        'events_by_tool': events_by_tool,
        'total_events': len(all_collected_events),
        'collected_events': all_collected_events,  # ← Add this
    }
```

---

### **Step 3: Create Session Aggregator**

**File:** `application/session_aggregator.py` (create new file)

Copy the entire `session_aggregator.py` from this reference folder.

Key method:
```python
def aggregate_events_to_sessions(self, events):
    # Group events by user_id
    # Calculate session metrics
    # Return list of SessionInput dicts
```

---

### **Step 4: Create Behavior Agent Client**

**File:** `integrations/behavior_agent_client.py` (create new file)

Copy the entire `behavior_agent_client.py` from this reference folder.

Key method:
```python
def send_sessions(self, sessions, pipeline_mode=False):
    # POST to http://127.0.0.1:8000/api/v1/behavior/batch/
    # Return {ok, sessions_sent, flagged_count, results}
```

**Dependencies:** Install `httpx` if not already installed:
```bash
pip install httpx
```

---

### **Step 5: Add Pipeline Orchestration**

**File:** `application/data_service.py` (or equivalent)

Add these methods:

```python
def __init__(self):
    # ... existing code ...
    from ..application.session_aggregator import SessionAggregator
    from ..integrations.behavior_agent_client import BehaviorAgentClient
    
    self.session_aggregator = SessionAggregator()
    self.behavior_client = BehaviorAgentClient()

def collect_and_forward_to_behavior(self, collectors):
    """Main pipeline orchestration method."""
    
    # Step 1: Collect events
    collection_result = self.collect_events(collectors)
    if not collection_result.get('ok'):
        return {...}  # Return error
    
    # Step 2: Extract events
    all_events = self._extract_events_from_collection(collection_result)
    if not all_events:
        return {...}  # Return error
    
    # Step 3: Aggregate to sessions
    sessions = self.session_aggregator.aggregate_events_to_sessions(all_events)
    if not sessions:
        return {...}  # Return error
    
    # Step 4: Send to Behavior Agent
    behavior_result = self.behavior_client.send_sessions(sessions, pipeline_mode=True)
    
    # Step 5: Return combined result
    return {
        **collection_result,
        'sessions_created': len(sessions),
        'behavior_result': behavior_result,
    }

def _extract_events_from_collection(self, collection_result):
    """Extract events from collection result."""
    return collection_result.get('collected_events', [])
```

---

### **Step 6: Update collect_events() Method**

**File:** `application/data_service.py`

Ensure `collect_events()` returns `collected_events`:

```python
def collect_events(self, collectors):
    result = self.mcp_manager.run_agent_iteration(collectors)
    
    return {
        'ok': True,
        'llm_reasoning': result.get('llm_reasoning', ''),
        'tools_executed': result.get('tools_executed', []),
        'events_by_tool': result.get('events_by_tool', {}),
        'total_events': result.get('total_events', 0),
        'collected_events': result.get('collected_events', []),  # ← Add this
        'timestamp': datetime.now().isoformat(),
    }
```

---

## ✅ Verification Checklist

After implementing the fix, verify:

- [ ] Pipeline endpoint exists: `/api/v1/data/pipeline-collect/`
- [ ] `collect_events()` returns `collected_events` list
- [ ] `SessionAggregator` class exists and works
- [ ] `BehaviorAgentClient` class exists and works
- [ ] `collect_and_forward_to_behavior()` method exists
- [ ] `_extract_events_from_collection()` method exists
- [ ] `httpx` library is installed

---

## 🧪 Testing the Fix

1. **Start the backend:**
   ```bash
   python manage.py runserver
   ```

2. **Click "Start Pipeline with Real Data" in frontend**

3. **Check logs for:**
   ```
   [data_agent] Pipeline mode: Collecting events and forwarding to Behavior Agent
   [data_agent] Extracted 150 events from collection
   [data_agent] Aggregated 150 events into 3 sessions
   [data_agent] Sending 3 session(s) to Behavior Agent
   [behavior_agent] Received 3 sessions for batch analysis
   [data_agent] Pipeline complete: 150 events → 3 sessions → Behavior Agent (1 flagged)
   ```

4. **Verify response includes:**
   ```json
   {
     "ok": true,
     "total_events": 150,
     "sessions_created": 3,
     "behavior_result": {
       "ok": true,
       "sessions_sent": 3,
       "flagged_count": 1,
       "results": [...]
     }
   }
   ```

---

## 📊 Expected Data Flow

```
User clicks "Start Pipeline"
    ↓
Frontend: POST /api/v1/data/pipeline-collect/
    ↓
PipelineCollectView.post()
    ↓
data_service.collect_and_forward_to_behavior()
    ├─ collect_events() → Returns {collected_events: [...]}
    ├─ _extract_events_from_collection() → Extracts event list
    ├─ session_aggregator.aggregate_events_to_sessions() → Creates sessions
    └─ behavior_client.send_sessions() → HTTP POST to Behavior Agent
        ↓
    Behavior Agent: POST /api/v1/behavior/batch/
        ↓
    Returns: {results: [{anomaly_result: {...}}]}
    ↓
Frontend displays: "3 sessions analyzed, 1 flagged"
```

---

## 🔧 Common Issues and Solutions

### **Issue 1: "No events to forward"**
**Cause:** `collected_events` not being tracked
**Fix:** Add event tracking in Step 2

### **Issue 2: "No sessions created"**
**Cause:** Session aggregator not working
**Fix:** Copy `session_aggregator.py` from reference

### **Issue 3: "Failed to send sessions"**
**Cause:** Behavior Agent client missing or wrong URL
**Fix:** Copy `behavior_agent_client.py` and verify URL

### **Issue 4: "Connection refused"**
**Cause:** Behavior Agent not running
**Fix:** Start Django backend on port 8000

### **Issue 5: "Module not found: httpx"**
**Cause:** Missing dependency
**Fix:** `pip install httpx`

---

## 📚 Reference Files in This Folder

1. **`README.md`** - Overview and problem description
2. **`api/views.py`** - Pipeline endpoint implementation
3. **`api/urls.py`** - URL routing
4. **`application/data_service.py`** - Pipeline orchestration
5. **`application/session_aggregator.py`** - Event-to-session conversion
6. **`integrations/behavior_agent_client.py`** - HTTP client for Behavior Agent
7. **`infrastructure/mcp_integration_EXCERPT.py`** - Event tracking example
8. **`behavior_agent/api/views_EXCERPT.py`** - Receiving side reference

---

## 🎯 Success Criteria

The fix is complete when:
1. ✅ Pipeline endpoint responds successfully
2. ✅ Events are collected and tracked
3. ✅ Sessions are created from events
4. ✅ Sessions are sent to Behavior Agent via HTTP
5. ✅ Behavior Agent analyzes sessions
6. ✅ Results are returned to frontend
7. ✅ Frontend displays flagged sessions

---

## 💡 Key Takeaways

The pipeline requires **5 components**:
1. **Endpoint** - Entry point for pipeline requests
2. **Event Tracking** - Store events in a list during collection
3. **Session Aggregation** - Convert events to session format
4. **HTTP Client** - Send sessions to Behavior Agent
5. **Orchestration** - Tie everything together

All 5 must work together for the pipeline to function.

---

Good luck! 🚀

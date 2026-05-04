# Event-Storage MCP Server

Provides persistent storage and querying capabilities for StandardEvent objects. Stores events in JSON Lines format organized by date and supports filtering, pagination, summary statistics, and export to mailbox for Team 2 consumption.

## Overview

The Event-Storage MCP Server exposes 4 tools for managing event data:

1. **store_events** - Persist StandardEvent objects to disk
2. **query_events** - Filter and retrieve events with pagination
3. **get_summary** - Get statistics about stored events
4. **export_to_mailbox** - Export filtered events for Team 2

## Storage Format

Events are stored in JSON Lines format (one event per line) organized by date:

```
logs/
├── events_2024-01-15.jsonl
├── events_2024-01-16.jsonl
└── events_2024-01-17.jsonl
```

Each line in a `.jsonl` file is a complete StandardEvent JSON object with no indentation.

## Tools

### 1. store_events

Persist an array of StandardEvent dictionaries to disk.

**Parameters:**
- `events` (array, required): Array of StandardEvent dictionaries

**Returns:**
```json
{
  "stored_count": 150,
  "files_written": ["logs/events_2024-01-15.jsonl"],
  "total_events": 150
}
```

**Example Usage (ADK Agent):**

```python
# Store collected events
result = await agent.call_tool(
    "event-storage",
    "store_events",
    {
        "events": [
            {
                "event_id": "uuid",
                "timestamp": "2024-01-15T10:30:00",
                "user_id": "U001",
                "device_id": "WORKSTATION-01",
                "event_type": "file_access",
                "event_category": "file",
                "action": "read",
                "resource": "C:\\Documents\\report.xlsx",
                "metadata": {"file_size_bytes": 1024},
                "source": "file_collector"
            }
        ]
    }
)
```

**Error Handling:**
- Returns validation errors for events that don't conform to StandardEvent schema
- Creates logs/ directory if it doesn't exist
- Appends to existing date files or creates new ones

---

### 2. query_events

Query stored events with filters and pagination.

**Parameters:**
- `event_type` (string, optional): Filter by event type
  - Values: "logon", "logoff", "file_access", "device_connect", "device_disconnect", "process_start", "process_stop", "network_connection", "http_request", "email_sent", "email_received"
- `event_category` (string, optional): Filter by event category
  - Values: "system", "file", "device", "process", "network", "web", "email"
- `user_id` (string, optional): Filter by user ID
- `device_id` (string, optional): Filter by device ID
- `start_time` (string, optional): Filter by start time (ISO 8601 format, inclusive)
- `end_time` (string, optional): Filter by end time (ISO 8601 format, inclusive)
- `page_size` (integer, optional): Number of events per page (default: 100, max: 1000)
- `page` (integer, optional): Page number, 1-indexed (default: 1)

**Returns:**
```json
{
  "events": [...],
  "count": 100,
  "total_matches": 1500,
  "page": 1,
  "page_size": 100,
  "has_more": true
}
```

**Example Usage:**

```python
# Query file access events for a specific user
result = await agent.call_tool(
    "event-storage",
    "query_events",
    {
        "event_type": "file_access",
        "user_id": "U001",
        "start_time": "2024-01-15T00:00:00",
        "end_time": "2024-01-15T23:59:59",
        "page_size": 50,
        "page": 1
    }
)

# Query all email events
result = await agent.call_tool(
    "event-storage",
    "query_events",
    {
        "event_category": "email"
    }
)

# Paginate through results
page = 1
while True:
    result = await agent.call_tool(
        "event-storage",
        "query_events",
        {
            "event_type": "network_connection",
            "page_size": 100,
            "page": page
        }
    )
    
    process_events(result["events"])
    
    if not result["has_more"]:
        break
    
    page += 1
```

**Filter Behavior:**
- All filters are combined with AND logic (all must match)
- Time range filtering is inclusive (events at start_time and end_time are included)
- Returns empty array with message if no matches found
- Uses memory-efficient streaming for large datasets

---

### 3. get_summary

Get summary statistics about all stored events.

**Parameters:** None

**Returns:**
```json
{
  "total_events": 5000,
  "events_by_type": {
    "logon": 150,
    "file_access": 2500,
    "network_connection": 1200,
    "email_sent": 350
  },
  "events_by_category": {
    "system": 150,
    "file": 2500,
    "network": 1200,
    "email": 350
  },
  "unique_users": 25,
  "unique_devices": 15,
  "time_range": {
    "earliest": "2024-01-15T08:00:00",
    "latest": "2024-01-17T18:30:00"
  }
}
```

**Example Usage:**

```python
# Get overview of stored data
summary = await agent.call_tool(
    "event-storage",
    "get_summary",
    {}
)

print(f"Total events: {summary['total_events']}")
print(f"Unique users: {summary['unique_users']}")
print(f"Time range: {summary['time_range']['earliest']} to {summary['time_range']['latest']}")
```

---

### 4. export_to_mailbox

Export filtered events to `mailbox/clean_events.json` for Team 2 consumption.

**Parameters:**
- `event_type` (string, optional): Filter by event type
- `event_category` (string, optional): Filter by event category
- `user_id` (string, optional): Filter by user ID
- `device_id` (string, optional): Filter by device ID
- `start_time` (string, optional): Filter by start time (ISO 8601 format)
- `end_time` (string, optional): Filter by end time (ISO 8601 format)

**Returns:**
```json
{
  "success": true,
  "events_exported": 1500,
  "export_file": "mailbox/clean_events.json",
  "metadata_file": "mailbox/clean_events_metadata.json",
  "export_timestamp": "2024-01-17T12:00:00"
}
```

**Export Format:**

The exported `mailbox/clean_events.json` file contains:
- JSON array of StandardEvent dictionaries
- Human-readable formatting (indent=2)
- Events sorted by timestamp in ascending order

The `mailbox/clean_events_metadata.json` file contains:
```json
{
  "export_timestamp": "2024-01-17T12:00:00",
  "event_count": 1500,
  "time_range": {
    "start": "2024-01-15T08:00:00",
    "end": "2024-01-17T18:30:00"
  },
  "data_source": "event_storage_mcp",
  "schema_version": "1.0",
  "filters_applied": {
    "event_type": null,
    "event_category": "file",
    "user_id": null,
    "device_id": null,
    "start_time": "2024-01-15T00:00:00",
    "end_time": "2024-01-17T23:59:59"
  }
}
```

**Example Usage:**

```python
# Export all file events for Team 2
result = await agent.call_tool(
    "event-storage",
    "export_to_mailbox",
    {
        "event_category": "file",
        "start_time": "2024-01-15T00:00:00",
        "end_time": "2024-01-17T23:59:59"
    }
)

print(f"Exported {result['events_exported']} events to {result['export_file']}")

# Export all events (no filters)
result = await agent.call_tool(
    "event-storage",
    "export_to_mailbox",
    {}
)
```

**Export Behavior:**
- Creates mailbox/ directory if it doesn't exist
- Overwrites existing clean_events.json and clean_events_metadata.json files
- Applies same filters as query_events
- Sorts events by timestamp before export

## Error Handling

All tools return structured error responses:

```json
{
  "error": {
    "type": "validation_error",
    "message": "Missing required fields: event_id, timestamp",
    "timestamp": "2024-01-17T12:00:00",
    "details": {
      "index": 5
    }
  }
}
```

**Error Types:**
- `validation_error`: Invalid parameters or event schema violations
- `internal_error`: File system errors or unexpected exceptions

## Concurrent Access

The Event-Storage MCP Server supports concurrent read operations:
- Uses file locking (fcntl on Unix, msvcrt on Windows) for safe concurrent queries
- Multiple agents can query simultaneously without data corruption
- Corrupted event files are skipped with warning logs

## Performance

- **Storage**: Stores 1000 events in ~5 seconds
- **Query**: Queries 10,000 events with filters in ~3 seconds
- **Memory**: Uses generator pattern for memory-efficient streaming
- **Pagination**: Recommended page_size is 100-500 for optimal performance

## Logging

All operations are logged to `logs/event_storage.log`:

```
2024-01-17 12:00:00 - event_storage - INFO - Tool invoked: store_events with arguments: {'events': [...]}
2024-01-17 12:00:01 - event_storage - INFO - Stored 150 events to logs/events_2024-01-17.jsonl
2024-01-17 12:00:05 - event_storage - INFO - Query returned 100 events (page 1, total matches: 1500)
2024-01-17 12:00:10 - event_storage - WARNING - Corrupted event in logs/events_2024-01-15.jsonl line 42
```

## Integration with Phase 3

The Event-Storage MCP Server is designed for use by Phase 3 ADK agents:

**Data Engineering Agent Workflow:**
```python
# 1. Collect events from collectors
system_events = await agent.call_tool("collector-executor", "collect_system_events", {})

# 2. Store collected events
await agent.call_tool("event-storage", "store_events", {
    "events": system_events["events"]
})

# 3. Query specific events for analysis
file_events = await agent.call_tool("event-storage", "query_events", {
    "event_category": "file",
    "start_time": "2024-01-15T00:00:00"
})

# 4. Export for Team 2
await agent.call_tool("event-storage", "export_to_mailbox", {
    "event_category": "file"
})
```

## Requirements Mapping

This implementation satisfies the following requirements:

- **Requirement 2.1**: store_events persists StandardEvent dictionaries
- **Requirement 2.2**: Events organized by date in logs/events_YYYY-MM-DD.jsonl
- **Requirement 2.3**: query_events with filter parameters
- **Requirement 2.4**: get_summary returns statistics
- **Requirement 2.5**: export_to_mailbox writes to mailbox/clean_events.json
- **Requirement 2.6**: ISO 8601 timestamp parsing with inclusive range filtering
- **Requirement 2.7**: Event validation against StandardEvent schema
- **Requirement 2.8**: Pagination support (page_size, page parameters)
- **Requirement 2.9**: Empty array with message for no matches
- **Requirement 2.10**: stdio transport for ADK communication
- **Requirement 2.11**: Concurrent read safety with file locking
- **Requirement 2.12**: Creates mailbox/ directory if needed

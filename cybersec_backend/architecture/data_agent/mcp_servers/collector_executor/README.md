# Collector-Executor MCP Server

The Collector-Executor MCP Server exposes Phase 1 data collectors as MCP tools for Google Agent Developer Kit (ADK) AI agents. It enables on-demand execution of all 11 collectors and returns StandardEvent objects.

## Overview

This server wraps the Phase 1 data collection layer, allowing AI agents to:
- Execute collectors on-demand to gather fresh system data
- Collect events from various sources (system, network, files, processes, browser, email, etc.)
- Receive validated StandardEvent objects as JSON-serializable dictionaries
- Handle time-range parameters for historical data collection

## Available Tools

### 1. collect_system_events
Collect system events (logon/logoff, active sessions, idle time).

**Parameters:** None

**Returns:**
```json
{
  "events": [StandardEvent, ...],
  "count": 1,
  "collector": "system_collector",
  "execution_time_ms": 125.5
}
```

### 2. collect_file_events
Collect file access events (read, write, create, delete operations).

**Parameters:** None

**Returns:** Same format as above

### 3. collect_network_events
Collect network connection events (active connections, protocols, ports).

**Parameters:** None

**Returns:** Same format as above

### 4. collect_process_events
Collect process events (running processes, CPU/memory usage, command lines).

**Parameters:** None

**Returns:** Same format as above

### 5. collect_browser_events
Collect browser history from Chrome and Edge (visited URLs, domains, page titles).

**Parameters:**
- `hours_back` (integer, optional): Number of hours to look back for browser history (default: 24, range: 1-720)

**Returns:** Same format as above

### 6. collect_email_events
Collect email metadata from Outlook (sent/received emails, external recipients, attachments).

**Parameters:**
- `hours_back` (integer, optional): Number of hours to look back for emails (default: 24, range: 1-720)

**Returns:** Same format as above

### 7. collect_windows_events
Collect Windows Event Log entries (security events, logon/logoff, privilege use).

**Parameters:**
- `hours_back` (integer, optional): Number of hours to look back for Windows events (default: 24, range: 1-720)

**Returns:** Same format as above

### 8. collect_usb_events
Collect USB device connection events (device type, vendor, product, serial number).

**Parameters:** None

**Returns:** Same format as above

### 9. collect_clipboard_events
Collect clipboard activity (clipboard content, sensitivity level, patterns detected).

**Parameters:** None

**Returns:** Same format as above

### 10. collect_registry_events
Collect Windows Registry changes (suspicious keys, autorun entries, persistence mechanisms).

**Parameters:** None

**Returns:** Same format as above

### 11. collect_dns_events
Collect DNS query history (domains queried, DNS record types, responses).

**Parameters:**
- `hours_back` (integer, optional): Number of hours to look back for DNS queries (default: 24, range: 1-720)

**Returns:** Same format as above

## StandardEvent Schema

All collectors return events conforming to the StandardEvent schema:

```json
{
  "event_id": "uuid",
  "timestamp": "2024-01-15T10:30:00",
  "user_id": "U001",
  "device_id": "WORKSTATION-01",
  "event_type": "file_access",
  "event_category": "file",
  "action": "read",
  "resource": "C:\\Documents\\report.xlsx",
  "metadata": {
    "file_path": "C:\\Documents\\report.xlsx",
    "file_size_bytes": 1024000,
    "sensitivity_level": 1
  },
  "source": "file_collector"
}
```

## Error Handling

The server returns structured error responses for failures:

### Timeout Error
```json
{
  "error": {
    "type": "timeout_error",
    "message": "Collector execution exceeded 30 second timeout",
    "details": {
      "collector": "email_collector",
      "elapsed_time_ms": 30500
    }
  }
}
```

### Dependency Error
```json
{
  "error": {
    "type": "dependency_error",
    "message": "Collector module not found: unknown_collector",
    "details": {
      "collector": "unknown_collector"
    }
  }
}
```

### Permission Error (Partial Results)
```json
{
  "events": [],
  "count": 0,
  "collector": "windows_event_collector",
  "execution_time_ms": 50.2,
  "warning": "Permission denied: Access is denied"
}
```

## Usage Examples

### Example 1: Collect System Events

```python
# Using Google ADK
from google.adk import Agent

agent = Agent()
result = agent.call_tool("collector-executor", "collect_system_events", {})

print(f"Collected {result['count']} system events")
for event in result['events']:
    print(f"  - {event['event_type']}: {event['resource']}")
```

### Example 2: Collect Browser History (Last 48 Hours)

```python
result = agent.call_tool("collector-executor", "collect_browser_events", {
    "hours_back": 48
})

print(f"Collected {result['count']} browser events in {result['execution_time_ms']}ms")
```

### Example 3: Collect Email Events with Error Handling

```python
result = agent.call_tool("collector-executor", "collect_email_events", {
    "hours_back": 24
})

if "error" in result:
    print(f"Error: {result['error']['message']}")
elif "warning" in result:
    print(f"Warning: {result['warning']}")
    print(f"Partial results: {result['count']} events")
else:
    print(f"Success: {result['count']} events collected")
```

### Example 4: Collect All Events

```python
collectors = [
    "collect_system_events",
    "collect_file_events",
    "collect_network_events",
    "collect_process_events",
    "collect_browser_events",
    "collect_email_events",
    "collect_windows_events",
    "collect_usb_events",
    "collect_clipboard_events",
    "collect_registry_events",
    "collect_dns_events",
]

all_events = []
for collector in collectors:
    result = agent.call_tool("collector-executor", collector, {})
    if "events" in result:
        all_events.extend(result["events"])

print(f"Total events collected: {len(all_events)}")
```

## Configuration

The server is configured in `mcp_config.json`:

```json
{
  "mcpServers": {
    "collector-executor": {
      "command": "python",
      "args": ["-m", "mcp_servers.collector_executor.server"],
      "transport": "stdio"
    }
  }
}
```

## Logging

All operations are logged to `logs/collector_executor.log`:

```
2024-01-15 10:30:00 - collector_executor - INFO - Tool invoked: collect_system_events with arguments: {}
2024-01-15 10:30:00 - collector_executor - INFO - Executing collector: system_collector (hours_back=None)
2024-01-15 10:30:00 - collector_executor - INFO - Collector system_collector completed: 1 events in 125.50ms
```

## Performance

- **Timeout:** All collectors have a 30-second execution timeout
- **Validation:** All events are validated against StandardEvent schema before return
- **Isolation:** Each collector invocation runs in an isolated context (no state leakage)

## Requirements

- Python 3.10+
- MCP Python SDK: `pip install mcp`
- Phase 1 collectors installed and functional
- Required collector dependencies (pywin32, psutil, watchdog, etc.)

## Testing

Run the server manually for testing:

```bash
python -m mcp_servers.collector_executor.server
```

The server will listen on stdio and wait for JSON-RPC messages from ADK agents.

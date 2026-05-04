"""
Tool definitions for Collector-Executor MCP Server.

Defines JSON Schema tool definitions for all 11 Phase 1 collectors.
"""

from mcp.types import Tool

# Standard event schema reference for return types
STANDARD_EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "event_id": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "user_id": {"type": "string"},
        "device_id": {"type": "string"},
        "event_type": {"type": "string"},
        "event_category": {"type": "string"},
        "action": {"type": "string"},
        "resource": {"type": "string"},
        "metadata": {"type": "object"},
        "source": {"type": "string"}
    },
    "required": ["event_id", "timestamp", "user_id", "device_id", "event_type", 
                 "event_category", "action", "resource", "metadata", "source"]
}

# Tool definitions for all 11 collectors
COLLECTOR_TOOLS = [
    Tool(
        name="collect_system_events",
        description="Collect system events (logon/logoff, active sessions, idle time)",
        inputSchema={
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    ),
    Tool(
        name="collect_file_events",
        description="Collect file access events (read, write, create, delete operations)",
        inputSchema={
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    ),
    Tool(
        name="collect_network_events",
        description="Collect network connection events (active connections, protocols, ports)",
        inputSchema={
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    ),
    Tool(
        name="collect_process_events",
        description="Collect process events (running processes, CPU/memory usage, command lines)",
        inputSchema={
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    ),
    Tool(
        name="collect_browser_events",
        description="Collect browser history from Chrome and Edge (visited URLs, domains, page titles)",
        inputSchema={
            "type": "object",
            "properties": {
                "hours_back": {
                    "type": "integer",
                    "description": "Number of hours to look back for browser history",
                    "default": 24,
                    "minimum": 1,
                    "maximum": 720
                }
            },
            "additionalProperties": False
        }
    ),
    Tool(
        name="collect_email_events",
        description="Collect email metadata from Outlook (sent/received emails, external recipients, attachments)",
        inputSchema={
            "type": "object",
            "properties": {
                "hours_back": {
                    "type": "integer",
                    "description": "Number of hours to look back for emails",
                    "default": 24,
                    "minimum": 1,
                    "maximum": 720
                }
            },
            "additionalProperties": False
        }
    ),
    Tool(
        name="collect_windows_events",
        description="Collect Windows Event Log entries (security events, logon/logoff, privilege use)",
        inputSchema={
            "type": "object",
            "properties": {
                "hours_back": {
                    "type": "integer",
                    "description": "Number of hours to look back for Windows events",
                    "default": 24,
                    "minimum": 1,
                    "maximum": 720
                }
            },
            "additionalProperties": False
        }
    ),
    Tool(
        name="collect_usb_events",
        description="Collect USB device connection events (device type, vendor, product, serial number)",
        inputSchema={
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    ),
    Tool(
        name="collect_clipboard_events",
        description="Collect clipboard activity (clipboard content, sensitivity level, patterns detected)",
        inputSchema={
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    ),
    Tool(
        name="collect_registry_events",
        description="Collect Windows Registry changes (suspicious keys, autorun entries, persistence mechanisms)",
        inputSchema={
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    ),
    Tool(
        name="collect_dns_events",
        description="Collect DNS query history (domains queried, DNS record types, responses)",
        inputSchema={
            "type": "object",
            "properties": {
                "hours_back": {
                    "type": "integer",
                    "description": "Number of hours to look back for DNS queries",
                    "default": 24,
                    "minimum": 1,
                    "maximum": 720
                }
            },
            "additionalProperties": False
        }
    ),
]

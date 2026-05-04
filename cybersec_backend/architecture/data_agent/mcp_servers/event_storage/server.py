"""
Event-Storage MCP Server

Provides persistent storage and querying capabilities for StandardEvent objects.
Stores events in JSON Lines format and supports filtering, pagination, and export.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mcp_servers.common.utils import setup_logger, create_error_response, create_success_response
from collectors.event_schema import StandardEvent

# Initialize logger
logger = setup_logger("event_storage", "logs/event_storage.log")

# Initialize MCP server
app = Server("event-storage")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List all available event storage tools."""
    return [
        Tool(
            name="store_events",
            description="Persist an array of StandardEvent objects to disk in JSON Lines format",
            inputSchema={
                "type": "object",
                "properties": {
                    "events": {
                        "type": "array",
                        "description": "Array of StandardEvent dictionaries to store",
                        "items": {"type": "object"}
                    }
                },
                "required": ["events"]
            }
        ),
        Tool(
            name="query_events",
            description="Query stored events with filters and pagination",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "description": "Filter by event type",
                        "enum": ["logon", "logoff", "file_access", "device_connect", 
                                "device_disconnect", "process_start", "process_stop",
                                "network_connection", "http_request", "email_sent", "email_received"]
                    },
                    "event_category": {
                        "type": "string",
                        "description": "Filter by event category",
                        "enum": ["system", "file", "device", "process", "network", "web", "email"]
                    },
                    "user_id": {
                        "type": "string",
                        "description": "Filter by user ID"
                    },
                    "device_id": {
                        "type": "string",
                        "description": "Filter by device ID"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Filter by start time (ISO 8601 format)",
                        "format": "date-time"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Filter by end time (ISO 8601 format)",
                        "format": "date-time"
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Number of events per page",
                        "default": 100,
                        "minimum": 1,
                        "maximum": 1000
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (1-indexed)",
                        "default": 1,
                        "minimum": 1
                    }
                }
            }
        ),
        Tool(
            name="get_summary",
            description="Get summary statistics about stored events",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="export_to_mailbox",
            description="Export filtered events to mailbox/clean_events.json for Team 2",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "description": "Filter by event type"
                    },
                    "event_category": {
                        "type": "string",
                        "description": "Filter by event category"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "Filter by user ID"
                    },
                    "device_id": {
                        "type": "string",
                        "description": "Filter by device ID"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Filter by start time (ISO 8601 format)"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Filter by end time (ISO 8601 format)"
                    }
                }
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Execute an event storage tool."""
    logger.info(f"Tool invoked: {name} with arguments: {arguments}")
    
    try:
        if name == "store_events":
            from mcp_servers.event_storage.storage_engine import store_events
            result = store_events(arguments.get("events", []))
        
        elif name == "query_events":
            from mcp_servers.event_storage.query_engine import query_events
            result = query_events(
                event_type=arguments.get("event_type"),
                event_category=arguments.get("event_category"),
                user_id=arguments.get("user_id"),
                device_id=arguments.get("device_id"),
                start_time=arguments.get("start_time"),
                end_time=arguments.get("end_time"),
                page_size=arguments.get("page_size", 100),
                page=arguments.get("page", 1)
            )
        
        elif name == "get_summary":
            from mcp_servers.event_storage.query_engine import get_summary
            result = get_summary()
        
        elif name == "export_to_mailbox":
            from mcp_servers.event_storage.query_engine import export_to_mailbox
            result = export_to_mailbox(
                event_type=arguments.get("event_type"),
                event_category=arguments.get("event_category"),
                user_id=arguments.get("user_id"),
                device_id=arguments.get("device_id"),
                start_time=arguments.get("start_time"),
                end_time=arguments.get("end_time")
            )
        
        else:
            result = create_error_response(
                "validation_error",
                f"Unknown tool: {name}",
                {"available_tools": ["store_events", "query_events", "get_summary", "export_to_mailbox"]}
            )
        
        return [TextContent(type="text", text=json.dumps(result))]
    
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        error_response = create_error_response(
            "internal_error",
            f"Unexpected error: {str(e)}",
            {"tool": name}
        )
        return [TextContent(type="text", text=json.dumps(error_response))]


async def main():
    """Main entry point for the MCP server."""
    logger.info("Starting Event-Storage MCP Server")
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

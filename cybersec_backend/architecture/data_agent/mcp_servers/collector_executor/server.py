"""
Collector-Executor MCP Server

Exposes Phase 1 data collectors as MCP tools for Google ADK agents.
Executes collectors on-demand and returns StandardEvent objects.
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
logger = setup_logger("collector_executor", "logs/collector_executor.log")

# Initialize MCP server
app = Server("collector-executor")

# Collector timeout in seconds
COLLECTOR_TIMEOUT = 30


def execute_collector(collector_module: str, hours_back: int = None) -> Dict[str, Any]:
    """
    Execute a collector module and return results.
    
    Args:
        collector_module: Name of the collector module (e.g., 'system_collector')
        hours_back: Optional hours_back parameter for time-range collectors
    
    Returns:
        Dictionary with events, count, collector name, and execution time
    """
    import time
    import importlib
    import signal
    from contextlib import contextmanager
    
    start_time = time.time()
    
    # Timeout handler for Unix-like systems
    @contextmanager
    def timeout_context(seconds):
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Collector execution exceeded {seconds} second timeout")
        
        # Set up signal handler (only works on Unix-like systems)
        if hasattr(signal, 'SIGALRM'):
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
            try:
                yield
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        else:
            # Windows doesn't support SIGALRM, just execute without timeout
            yield
    
    try:
        logger.info(f"Executing collector: {collector_module} (hours_back={hours_back})")
        
        with timeout_context(COLLECTOR_TIMEOUT):
            # Import the collector module dynamically
            module = importlib.import_module(f"collectors.{collector_module}")
            
            # Map collector modules to their main collection functions
            collector_functions = {
                "system_collector": "collect_system_snapshot",
                "file_collector": "collect_file_snapshot",
                "network_collector": "collect_network_connections",
                "process_collector": "collect_running_processes",
                "browser_collector": "collect_browser_history",
                "email_collector": "collect_outlook_emails",
                "windows_event_collector": "collect_windows_events",
                "usb_device_collector": "collect_usb_device_history",
                "clipboard_collector": "monitor_clipboard",
                "registry_collector": "collect_persistence_mechanisms",
                "dns_collector": "collect_dns_queries",
            }
            
            func_name = collector_functions.get(collector_module)
            if not func_name:
                return create_error_response(
                    "internal_error",
                    f"Unknown collector function for module: {collector_module}",
                    {"collector": collector_module}
                )
            
            # Get the collection function
            collect_func = getattr(module, func_name)
            
            # Call the function with or without hours_back parameter
            collectors_with_hours_back = {
                "browser_collector", "email_collector", 
                "windows_event_collector", "dns_collector"
            }
            
            if collector_module in collectors_with_hours_back and hours_back is not None:
                events = collect_func(hours_back=hours_back)
            else:
                events = collect_func()
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Validate events against StandardEvent schema
        validated_events = []
        for event in events:
            try:
                # Events are already StandardEvent objects, convert to dict
                if hasattr(event, 'model_dump'):
                    validated_events.append(event.model_dump())
                else:
                    # If it's already a dict, validate it
                    validated_event = StandardEvent.model_validate(event)
                    validated_events.append(validated_event.model_dump())
            except Exception as e:
                logger.warning(f"Event validation failed: {e}")
                continue
        
        logger.info(f"Collector {collector_module} completed: {len(validated_events)} events in {execution_time_ms:.2f}ms")
        
        return {
            "events": validated_events,
            "count": len(validated_events),
            "collector": collector_module,
            "execution_time_ms": round(execution_time_ms, 2)
        }
    
    except TimeoutError as e:
        execution_time_ms = (time.time() - start_time) * 1000
        logger.error(f"Collector {collector_module} timed out after {COLLECTOR_TIMEOUT}s")
        return create_error_response(
            "timeout_error",
            str(e),
            {
                "collector": collector_module,
                "elapsed_time_ms": round(execution_time_ms, 2)
            }
        )
    
    except ModuleNotFoundError:
        logger.error(f"Collector module not found: {collector_module}")
        return create_error_response(
            "dependency_error",
            f"Collector module not found: {collector_module}",
            {"collector": collector_module}
        )
    
    except AttributeError as e:
        logger.error(f"Collector function not found in module {collector_module}: {e}")
        return create_error_response(
            "dependency_error",
            f"Collector function not found: {str(e)}",
            {"collector": collector_module}
        )
    
    except PermissionError as e:
        execution_time_ms = (time.time() - start_time) * 1000
        logger.warning(f"Permission error in collector {collector_module}: {e}")
        return {
            "events": [],
            "count": 0,
            "collector": collector_module,
            "execution_time_ms": round(execution_time_ms, 2),
            "warning": f"Permission denied: {str(e)}"
        }
    
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        logger.error(f"Unexpected error executing collector {collector_module}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return create_error_response(
            "internal_error",
            f"Unexpected error: {str(e)}",
            {
                "collector": collector_module,
                "execution_time_ms": execution_time_ms
            }
        )


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List all available collector tools."""
    from mcp_servers.collector_executor.tool_definitions import COLLECTOR_TOOLS
    return COLLECTOR_TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Execute a collector tool."""
    logger.info(f"Tool invoked: {name} with arguments: {arguments}")
    
    # Map tool names to collector modules
    tool_to_collector = {
        "collect_system_events": "system_collector",
        "collect_file_events": "file_collector",
        "collect_network_events": "network_collector",
        "collect_process_events": "process_collector",
        "collect_browser_events": "browser_collector",
        "collect_email_events": "email_collector",
        "collect_windows_events": "windows_event_collector",
        "collect_usb_events": "usb_device_collector",
        "collect_clipboard_events": "clipboard_collector",
        "collect_registry_events": "registry_collector",
        "collect_dns_events": "dns_collector",
    }
    
    if name not in tool_to_collector:
        error_response = create_error_response(
            "validation_error",
            f"Unknown tool: {name}",
            {"available_tools": list(tool_to_collector.keys())}
        )
        return [TextContent(type="text", text=json.dumps(error_response))]
    
    # Get collector module name
    collector_module = tool_to_collector[name]
    
    # Extract hours_back parameter if present
    hours_back = arguments.get("hours_back")
    
    # Execute collector
    result = execute_collector(collector_module, hours_back)
    
    # Return result as JSON
    return [TextContent(type="text", text=json.dumps(result))]


async def main():
    """Main entry point for the MCP server."""
    logger.info("Starting Collector-Executor MCP Server")
    logger.info(f"Available tools: {len(COLLECTOR_TOOLS)}")
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    # Import tool definitions here to avoid circular imports
    from mcp_servers.collector_executor.tool_definitions import COLLECTOR_TOOLS
    asyncio.run(main())

"""
Python-Executor MCP Server

Executes Python code safely in a sandboxed environment with restricted permissions.
Provides code execution capabilities for AI agents with security controls.
"""

import asyncio
import hashlib
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

# Initialize logger
logger = setup_logger("python_executor", "logs/python_executor.log")

# Initialize MCP server
app = Server("python-executor")


def compute_code_hash(code: str) -> str:
    """
    Compute SHA-256 hash of code for audit trail.
    
    Args:
        code: Python code string
    
    Returns:
        Hexadecimal SHA-256 hash
    """
    return hashlib.sha256(code.encode('utf-8')).hexdigest()


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List all available Python execution tools."""
    return [
        Tool(
            name="execute_code",
            description="Execute Python code in a sandboxed environment with configurable security profiles",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute"
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Execution timeout in seconds",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 30
                    },
                    "execution_mode": {
                        "type": "string",
                        "description": "Security profile: 'restricted' for data analysis (default), 'attack_simulation' for adversarial agents",
                        "enum": ["restricted", "attack_simulation"],
                        "default": "restricted"
                    }
                },
                "required": ["code"]
            }
        ),
        Tool(
            name="list_allowed_imports",
            description="Return the whitelist of permitted Python modules for a given execution mode",
            inputSchema={
                "type": "object",
                "properties": {
                    "execution_mode": {
                        "type": "string",
                        "description": "Execution mode to get imports for",
                        "enum": ["restricted", "attack_simulation"],
                        "default": "restricted"
                    }
                }
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Execute a Python execution tool."""
    logger.info(f"Tool invoked: {name} with arguments: {arguments}")
    
    try:
        if name == "execute_code":
            code = arguments.get("code", "")
            timeout_seconds = arguments.get("timeout_seconds", 10)
            execution_mode = arguments.get("execution_mode", "restricted")
            
            # Validate execution_mode
            if execution_mode not in ["restricted", "attack_simulation"]:
                result = create_error_response(
                    "validation_error",
                    f"Invalid execution_mode: {execution_mode}. Must be 'restricted' or 'attack_simulation'",
                    {"execution_mode": execution_mode}
                )
                return [TextContent(type="text", text=json.dumps(result))]
            
            # Validate code is not empty
            if not code or not code.strip():
                result = create_error_response(
                    "validation_error",
                    "Code parameter cannot be empty",
                    {}
                )
                return [TextContent(type="text", text=json.dumps(result))]
            
            # Compute code hash for logging
            code_hash = compute_code_hash(code)
            logger.info(f"Executing code (hash: {code_hash[:16]}..., mode: {execution_mode}, timeout: {timeout_seconds}s)")
            
            # Import execution logic here to avoid circular imports
            from mcp_servers.python_executor.sandbox_config import execute_code_in_sandbox
            
            # Execute code in sandbox with specified mode
            result = execute_code_in_sandbox(code, timeout_seconds, code_hash, execution_mode)
            
            # Log execution result
            if result.get("success"):
                logger.info(f"Code execution succeeded (hash: {code_hash[:16]}..., mode: {execution_mode}, time: {result.get('execution_time_ms')}ms)")
            else:
                error_type = result.get("error", {}).get("type", "unknown")
                logger.warning(f"Code execution failed (hash: {code_hash[:16]}..., mode: {execution_mode}, error: {error_type})")
        
        elif name == "list_allowed_imports":
            execution_mode = arguments.get("execution_mode", "restricted")
            
            # Validate execution_mode
            if execution_mode not in ["restricted", "attack_simulation"]:
                result = create_error_response(
                    "validation_error",
                    f"Invalid execution_mode: {execution_mode}. Must be 'restricted' or 'attack_simulation'",
                    {"execution_mode": execution_mode}
                )
                return [TextContent(type="text", text=json.dumps(result))]
            
            from mcp_servers.python_executor.sandbox_config import get_allowed_imports
            imports_list = get_allowed_imports(execution_mode)
            
            mode_descriptions = {
                "restricted": "Safe data analysis and transformation (default)",
                "attack_simulation": "Adversarial attack code generation with expanded imports"
            }
            
            result = {
                "execution_mode": execution_mode,
                "allowed_imports": sorted(list(imports_list)),
                "count": len(imports_list),
                "description": mode_descriptions[execution_mode]
            }
            logger.info(f"Listed {len(imports_list)} allowed imports for mode: {execution_mode}")
        
        else:
            result = create_error_response(
                "validation_error",
                f"Unknown tool: {name}",
                {"available_tools": ["execute_code", "list_allowed_imports"]}
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
    logger.info("Starting Python-Executor MCP Server")
    logger.info("Execution modes: RESTRICTED (default, data analysis) | ATTACK_SIMULATION (adversarial agents)")
    logger.info("Daytona cloud sandbox: Network blocked, code injection blocked, file/process isolation trusted")
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

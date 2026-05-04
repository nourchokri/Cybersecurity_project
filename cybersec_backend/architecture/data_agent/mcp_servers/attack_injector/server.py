"""
Attack-Injector MCP Server

Generates realistic attack simulations based on MITRE ATT&CK techniques.
Uses dataset-driven approach with attack patterns from data/attacks/attack_patterns.json.
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
logger = setup_logger("attack_injector", "logs/attack_injector.log")

# Initialize MCP server
app = Server("attack-injector")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List all available attack injection tools."""
    return [
        Tool(
            name="inject_attack",
            description="Generate realistic attack simulation events from dataset patterns",
            inputSchema={
                "type": "object",
                "properties": {
                    "attack_id": {
                        "type": "string",
                        "description": "Specific attack pattern ID from dataset (e.g., 'usb_exfil_financial_001')"
                    },
                    "category": {
                        "type": "string",
                        "description": "Attack category filter (e.g., 'data_exfiltration', 'credential_access', 'discovery')"
                    },
                    "mitre_technique": {
                        "type": "string",
                        "description": "MITRE ATT&CK technique ID (e.g., 'T1052.001', 'T1114.002')"
                    },
                    "severity": {
                        "type": "string",
                        "description": "Severity level filter (low, medium, high, critical)",
                        "enum": ["low", "medium", "high", "critical"]
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User to simulate attack for (optional, random if not provided)"
                    },
                    "device_id": {
                        "type": "string",
                        "description": "Device to simulate attack on (optional, random if not provided)"
                    },
                    "randomize": {
                        "type": "boolean",
                        "description": "Apply timing and resource randomization (default: true)",
                        "default": True
                    }
                }
            }
        ),
        Tool(
            name="list_attack_patterns",
            description="List all available attack patterns from dataset with optional filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by attack category"
                    },
                    "mitre_technique": {
                        "type": "string",
                        "description": "Filter by MITRE ATT&CK technique"
                    },
                    "severity": {
                        "type": "string",
                        "description": "Filter by severity level",
                        "enum": ["low", "medium", "high", "critical"]
                    }
                }
            }
        ),
        Tool(
            name="add_attack_pattern",
            description="Add a new attack pattern to the dataset (optional)",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "object",
                        "description": "Attack pattern object conforming to the dataset schema",
                        "required": ["id", "name", "category", "mitre_technique", "severity", "description", "sequence"]
                    }
                },
                "required": ["pattern"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Execute an attack injection tool."""
    logger.info(f"Tool invoked: {name} with arguments: {arguments}")
    
    try:
        if name == "inject_attack":
            from mcp_servers.attack_injector.attack_generator import inject_attack
            result = inject_attack(
                attack_id=arguments.get("attack_id"),
                category=arguments.get("category"),
                mitre_technique=arguments.get("mitre_technique"),
                severity=arguments.get("severity"),
                user_id=arguments.get("user_id"),
                device_id=arguments.get("device_id"),
                randomize=arguments.get("randomize", True)
            )
        
        elif name == "list_attack_patterns":
            from mcp_servers.attack_injector.dataset_loader import list_attack_patterns
            result = list_attack_patterns(
                category=arguments.get("category"),
                mitre_technique=arguments.get("mitre_technique"),
                severity=arguments.get("severity")
            )
        
        elif name == "add_attack_pattern":
            from mcp_servers.attack_injector.dataset_loader import add_attack_pattern
            result = add_attack_pattern(arguments.get("pattern"))
        
        else:
            result = create_error_response(
                "validation_error",
                f"Unknown tool: {name}",
                {"available_tools": ["inject_attack", "list_attack_patterns", "add_attack_pattern"]}
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
    logger.info("Starting Attack-Injector MCP Server")
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

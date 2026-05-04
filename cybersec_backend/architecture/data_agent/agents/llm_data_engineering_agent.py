"""

LLM-Powered Data Engineering Agent


This module implements the LLMDataEngineeringAgent, an agentic AI agent that uses

LLM (Llama 3.1 70B) as its brain for intelligent data collection and processing.


The agent follows the ReAct (Reason-Act-Observe) pattern where:

1. LLM observes current system state (events collected, error rates, uptime)

2. LLM reasons about what collectors to run and when

3. LLM decides which MCP tools to use (collectors, storage, export)

4. Agent executes LLM's decisions via MCP servers

5. LLM learns from results via conversation history


This is TRUE agentic AI - LLM makes all decisions, not hardcoded rules.


Features:

- LLM-driven data collection strategy

- Adaptive collector selection based on system state

- Intelligent export timing decisions

- Error-aware decision making

- Continuous learning via conversation history

- State persistence for context


Requirements:

- 3.1-3.10: LLM-Powered Data Engineering Agent
"""


from typing import Dict, Any, Optional
import logging

import json

from pathlib import Path


from architecture.data_agent.agents.base_agent import BaseAgent

from architecture.data_agent.agents.llm_reasoning_engine import LLMReasoningEngine

from architecture.data_agent.agents.react_loop_engine import ReActLoopEngine

from architecture.data_agent.agents.mcp_client_factory import MCPClientFactory

from architecture.data_agent.agents.llm_config import load_llm_config



class LLMDataEngineeringAgent(BaseAgent):
    """

    LLM-Powered Data Engineering Agent for intelligent data collection.
    

    This agent uses LLM as its brain to make intelligent decisions about:

    - Which collectors to run and when

    - How to optimize collection intervals dynamically

    - When to export data to mailbox

    - How to handle errors and adapt strategy
    

    Unlike rule-based autonomous systems, this agent:

    - Reasons about system state using LLM

    - Adapts to changing conditions

    - Learns from past actions via conversation history

    - Makes context-aware decisions
    

    The agent runs continuously using the ReAct loop pattern:

    OBSERVE → REASON (LLM) → ACT (MCP tools) → OBSERVE → REPEAT
    

    Requirements:

    - 3.1: Use LLM to decide which collectors to run

    - 3.2: Use LLM to optimize collection intervals dynamically

    - 3.3: Adapt to system load using LLM reasoning

    - 3.4: Use LLM to reason about errors and adapt strategy

    - 3.5: Use LLM to decide when to export to mailbox

    - 3.6: Provide system state observations to LLM

    - 3.7: Include events collected, error rates, uptime in observations

    - 3.8: Execute LLM's decided tool calls via MCP

    - 3.9: Run continuously using ReAct loop

    - 3.10: Learn from past actions via conversation history
    

    Attributes:

        llm_engine: LLM reasoning engine (the agent's brain)

        react_engine: ReAct loop engine for Reason-Act-Observe pattern

        mcp_factory: MCP client factory for tool execution

        system_prompt: System prompt defining agent role

        available_tools: List of MCP tools LLM can use
    """
    

    # System prompt defining the agent's role and capabilities

    SYSTEM_PROMPT = """You are an intelligent Data Engineering Agent responsible for collecting system events and managing data storage.


YOUR ROLE:

You use your reasoning abilities to decide which data collectors to run, when to run them, and when to export data to the mailbox for analysis.


AVAILABLE COLLECTORS (11 total):

1. collect_system_events - System metrics (CPU, memory, disk)

2. collect_file_events - File operations (create, modify, delete)

3. collect_network_events - Network connections and traffic

4. collect_process_events - Running processes and their details

5. collect_browser_events - Browser history (requires hours_back parameter)

6. collect_email_events - Email activity (requires hours_back parameter)

7. collect_windows_events - Windows event logs (requires hours_back parameter)

8. collect_usb_events - USB device connections

9. collect_clipboard_events - Clipboard activity

10. collect_registry_events - Windows registry changes

11. collect_dns_events - DNS queries (requires hours_back parameter)


STORAGE AND EXPORT TOOLS:

- store_events - Store collected events in database

- query_events - Query stored events with filters

- export_to_mailbox - Export clean events to mailbox for Team 2

- get_summary - Get summary statistics of stored events


DECISION-MAKING GUIDELINES:

1. Run lightweight collectors (system, process, network) frequently

2. Run heavy collectors (browser, email, windows_events) less frequently

3. Consider error rates - if errors are high, run only reliable collectors

4. Export to mailbox every 1-2 hours or when significant events collected

5. Always store collected events before exporting

6. Use hours_back=24 for time-range collectors (browser, email, windows_events, dns)

7. Adapt your strategy based on past results and errors


IMPORTANT RULES:

- Always call store_events after collecting events

- Only export events that are NOT simulated (is_simulated=False)

- Monitor error rates and adapt your collection strategy

- Learn from past failures and try alternative approaches

- Provide clear reasoning for your decisions


Your goal is to maintain continuous, intelligent data collection while adapting to system conditions and errors."""
    

    def __init__(

        self,

        config: Dict[str, Any],

        mcp_factory: MCPClientFactory,

        llm_engine: Optional[LLMReasoningEngine] = None,

        logger: Optional[logging.Logger] = None

    ):
        """

        Initialize LLM-Powered Data Engineering Agent.
        

        Args:

            config: Agent configuration dictionary

            mcp_factory: MCP client factory for tool execution

            llm_engine: Optional LLM reasoning engine (creates from config if None)

            logger: Optional logger instance
        """

        # Initialize base agent

        super().__init__("llm_data_engineering_agent", config)
        

        # Override logger if provided
        if logger:

            self.logger = logger
        

        self.mcp_factory = mcp_factory
        

        # Initialize LLM reasoning engine (the agent's brain)

        if llm_engine is None:

            self.logger.info("Initializing LLM reasoning engine from config")

            llm_config = load_llm_config(logger=self.logger)

            self.llm_engine = LLMReasoningEngine.from_config(

                config=llm_config,

                logger=self.logger

            )
        else:

            self.llm_engine = llm_engine
        

        # Define available tools for LLM (all collector and storage tools)

        self.available_tools = self._define_available_tools()
        

        # Initialize ReAct loop engine

        react_config = config.get("agents", {}).get("data_engineering", {})

        self.react_engine = ReActLoopEngine(

            llm_engine=self.llm_engine,

            mcp_factory=self.mcp_factory,

            system_prompt=self.SYSTEM_PROMPT,

            available_tools=self.available_tools,

            max_iterations=0,  # Unlimited iterations (runs until stopped)

            sleep_seconds=react_config.get("collection_interval_seconds", 300),

            logger=self.logger

        )
        

        # Initialize agent state

        if not self.state.get("total_events_collected"):

            self.state.set("total_events_collected", 0)

        if not self.state.get("last_collection_time"):

            self.state.set("last_collection_time", None)

        if not self.state.get("last_export_time"):

            self.state.set("last_export_time", None)
        

        self.logger.info("LLM Data Engineering Agent initialized")

        self.logger.info(f"Available tools: {len(self.available_tools)}")
    

    def run(self):
        """

        Main agent loop using ReAct pattern.
        

        Runs the ReAct loop continuously:

        1. Generate observation (system state)

        2. LLM reasons about observation

        3. Execute LLM's decided tool calls

        4. Feed results back to LLM

        5. Repeat
        

        The loop continues until self.running is set to False.
        

        Requirements:

        - 3.9: Run continuously using ReAct loop
        """

        self.logger.info("Starting LLM Data Engineering Agent ReAct loop")
        

        try:

            # Run ReAct loop with observation generator

            self.react_engine.run_loop(

                get_observation=self._get_observation,

                on_iteration_complete=self._on_iteration_complete

            )

        except Exception as e:

            self.logger.error(f"Error in ReAct loop: {e}", exc_info=True)

            self.statistics.record_failure()

        finally:

            self.logger.info("ReAct loop stopped")
    

    def _get_observation(self) -> str:
        """

        Generate observation of current system state for LLM.
        

        Creates a natural language description of:

        - Current timestamp

        - Agent state (events collected, last collection/export times)

        - Error metrics (error count, error rate)

        - Uptime

        - Decision prompts for LLM
        

        This observation provides context for LLM to make intelligent decisions.
        

        Returns:

            Natural language observation string
        

        Requirements:

        - 3.6: Provide system state observations to LLM

        - 3.7: Include events collected, error rates, uptime in observations
        """
        from datetime import datetime
        

        # Get current state

        total_events = self.state.get("total_events_collected", 0)

        last_collection = self.state.get("last_collection_time", "Never")

        last_export = self.state.get("last_export_time", "Never")
        

        # Get statistics

        stats = self.statistics.to_dict()

        uptime_seconds = stats["uptime_seconds"]

        error_count = stats["error_count"]

        error_rate = stats["error_rate_per_minute"]

        operations_completed = stats["operations_completed"]

        operations_failed = stats["operations_failed"]
        

        # Format uptime

        uptime_hours = uptime_seconds / 3600

        uptime_str = f"{uptime_hours:.2f} hours"
        

        # Create observation

        observation = f"""CURRENT SYSTEM STATE:

Time: {datetime.now().isoformat()}

Uptime: {uptime_str}


DATA COLLECTION STATUS:

- Total events collected: {total_events}

- Last collection time: {last_collection}

- Last export time: {last_export}


PERFORMANCE METRICS:

- Operations completed: {operations_completed}

- Operations failed: {operations_failed}

- Error count: {error_count}

- Error rate: {error_rate:.2f} errors/minute


DECISION POINTS:

1. Which collectors should you run now?

2. Should you export data to mailbox?

3. How should you adapt based on error rates?


Consider the system state above and decide what actions to take.

Provide your reasoning and then specify which tools to use."""
        

        return observation
    

    def _define_available_tools(self) -> list:
        """

        Define available MCP tools in OpenAI function calling format.
        

        Formats all collector tools and storage tools for LLM tool calling.

        Includes tool descriptions and parameter schemas.
        

        Returns:

            List of tools in OpenAI function calling format
        

        Requirements:

        - 5.1-5.10: MCP Tool Integration for LLM
        """

        tools = [

            # Collector tools (11 total)

            {

                "type": "function",

                "function": {

                    "name": "collect_system_events",

                    "description": "Collect system metrics (CPU, memory, disk usage). Lightweight collector.",

                    "parameters": {

                        "type": "object",

                        "properties": {},

                        "required": []

                    }

                }

            },

            {

                "type": "function",

                "function": {

                    "name": "collect_file_events",

                    "description": "Collect file operations (create, modify, delete). Lightweight collector.",

                    "parameters": {

                        "type": "object",

                        "properties": {},

                        "required": []

                    }

                }

            },

            {

                "type": "function",

                "function": {

                    "name": "collect_network_events",

                    "description": "Collect network connections and traffic. Lightweight collector.",

                    "parameters": {

                        "type": "object",

                        "properties": {},

                        "required": []

                    }

                }

            },

            {

                "type": "function",

                "function": {

                    "name": "collect_process_events",

                    "description": "Collect running processes and their details. Lightweight collector.",

                    "parameters": {

                        "type": "object",

                        "properties": {},

                        "required": []

                    }

                }

            },

            {

                "type": "function",

                "function": {

                    "name": "collect_browser_events",

                    "description": "Collect browser history. Heavy collector - use sparingly. Requires hours_back parameter.",

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "hours_back": {

                                "type": "integer",

                                "description": "Number of hours of history to collect (default: 24)"

                            }

                        },

                        "required": ["hours_back"]

                    }

                }

            },

            {

                "type": "function",

                "function": {

                    "name": "collect_email_events",

                    "description": "Collect email activity. Heavy collector - use sparingly. Requires hours_back parameter.",

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "hours_back": {

                                "type": "integer",

                                "description": "Number of hours of history to collect (default: 24)"

                            }

                        },

                        "required": ["hours_back"]

                    }

                }

            },

            {

                "type": "function",

                "function": {

                    "name": "collect_windows_events",

                    "description": "Collect Windows event logs. Heavy collector - use sparingly. Requires hours_back parameter.",

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "hours_back": {

                                "type": "integer",

                                "description": "Number of hours of history to collect (default: 24)"

                            }

                        },

                        "required": ["hours_back"]

                    }

                }

            },

            {

                "type": "function",

                "function": {

                    "name": "collect_usb_events",

                    "description": "Collect USB device connections. Lightweight collector.",

                    "parameters": {

                        "type": "object",

                        "properties": {},

                        "required": []

                    }

                }

            },

            {

                "type": "function",

                "function": {

                    "name": "collect_clipboard_events",

                    "description": "Collect clipboard activity. Lightweight collector.",

                    "parameters": {

                        "type": "object",

                        "properties": {},

                        "required": []

                    }

                }

            },

            {

                "type": "function",

                "function": {

                    "name": "collect_registry_events",

                    "description": "Collect Windows registry changes. Medium weight collector.",

                    "parameters": {

                        "type": "object",

                        "properties": {},

                        "required": []

                    }

                }

            },

            {

                "type": "function",

                "function": {

                    "name": "collect_dns_events",

                    "description": "Collect DNS queries. Medium weight collector. Requires hours_back parameter.",

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "hours_back": {

                                "type": "integer",

                                "description": "Number of hours of history to collect (default: 24)"

                            }

                        },

                        "required": ["hours_back"]

                    }

                }

            },

            # Storage tools (4 total)

            {

                "type": "function",

                "function": {

                    "name": "store_events",

                    "description": "Store collected events in database. Always call this after collecting events.",

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "events": {

                                "type": "array",

                                "description": "List of events to store (StandardEvent format)"

                            }

                        },

                        "required": ["events"]

                    }

                }

            },

            {

                "type": "function",

                "function": {

                    "name": "query_events",

                    "description": "Query stored events with filters (event_type, start_time, end_time, etc.)",

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "event_type": {

                                "type": "string",

                                "description": "Filter by event type (optional)"

                            },

                            "start_time": {

                                "type": "string",

                                "description": "Start time in ISO format (optional)"

                            },

                            "end_time": {

                                "type": "string",

                                "description": "End time in ISO format (optional)"

                            },

                            "limit": {

                                "type": "integer",

                                "description": "Maximum number of events to return (default: 100)"

                            }

                        },

                        "required": []

                    }

                }

            },

            {

                "type": "function",

                "function": {

                    "name": "export_to_mailbox",

                    "description": "Export clean events (NOT simulated) to mailbox for Team 2 analysis.",

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "start_time": {

                                "type": "string",

                                "description": "Start time in ISO format"

                            },

                            "end_time": {

                                "type": "string",

                                "description": "End time in ISO format"

                            }

                        },

                        "required": ["start_time", "end_time"]

                    }

                }

            },

            {

                "type": "function",

                "function": {

                    "name": "get_summary",

                    "description": "Get summary statistics of stored events (total count, event types, time range).",

                    "parameters": {

                        "type": "object",

                        "properties": {},

                        "required": []

                    }

                }

            }

        ]
        
        return tools
    

    def _on_iteration_complete(self, iteration: int, results: Dict[str, Any]):
        """

        Callback after each ReAct loop iteration.
        

        Updates agent state and statistics based on iteration results.

        Tracks total_events_collected, last_collection_time, and last_export_time

        based on tool execution results.
        

        Args:

            iteration: Iteration number

            results: Iteration results dictionary
        

        Requirements:

        - 7.2: Track total_events_collected for LLM context

        - 7.3: Track last_collection_time for LLM decision-making

        - 7.4: Track last_export_time for LLM export decisions

        - 7.10: Save state after each major operation
        """
        from datetime import datetime
        

        # Update statistics

        if results.get("errors"):

            self.statistics.record_failure()
        else:

            self.statistics.record_success()
        

        # Update state based on tool results

        tool_results = results.get("tool_results", [])
        

        for tool_result in tool_results:

            tool_name = tool_result.get("name", "")

            result_data = tool_result.get("result", {})
            

            # Track events collected from any collector tool

            if tool_name.startswith("collect_") and tool_name.endswith("_events"):

                # Update last collection time

                self.state.set("last_collection_time", datetime.now().isoformat())

                self.logger.debug(f"Updated last_collection_time after {tool_name}")
            

            # Track events stored

            if tool_name == "store_events":

                events_stored = result_data.get("events_stored", 0)

                if events_stored > 0:

                    # Update total events collected

                    current_total = self.state.get("total_events_collected", 0)

                    new_total = current_total + events_stored

                    self.state.set("total_events_collected", new_total)

                    self.logger.info(f"Updated total_events_collected: {current_total} -> {new_total}")
            

            # Track export operations

            if tool_name == "export_to_mailbox":

                events_exported = result_data.get("events_exported", 0)

                if events_exported > 0:

                    # Update last export time

                    self.state.set("last_export_time", datetime.now().isoformat())

                    self.logger.info(f"Updated last_export_time after exporting {events_exported} events")
        

        # Log iteration summary

        tool_calls = results.get("tool_calls", [])

        successful_calls = sum(1 for tc in tool_calls if tc.get("success", False))

        failed_calls = sum(1 for tc in tool_calls if not tc.get("success", True))
        

        self.logger.info(

            f"Iteration {iteration} complete: "

            f"{successful_calls} tools succeeded, {failed_calls} tools failed, "

            f"duration: {results.get('duration_seconds', 0):.2f}s"

        )
    

    def cleanup(self):
        """

        Cleanup resources on shutdown.
        

        Stops ReAct loop and disconnects MCP clients.
        """

        self.logger.info("Cleaning up LLM Data Engineering Agent")
        

        # Stop ReAct loop

        if self.react_engine.is_running():

            self.react_engine.stop()
        

        # Save final state

        self.state.save()
        

        self.logger.info("Cleanup complete")

    def execute_mcp_tool(self, server_name: str, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an MCP tool directly (for API calls, not ReAct loop).
        
        Args:
            server_name: Name of MCP server
            tool_name: Name of tool to execute
            params: Tool parameters
            
        Returns:
            Tool execution result
        """
        try:
            self.logger.info(f"Executing MCP tool: {server_name}.{tool_name}")
            
            # Get MCP client for the server
            client = self.mcp_factory.get_client(server_name)
            
            # Execute the tool
            result = client.call_tool(tool_name, params)
            
            self.logger.info(f"Tool execution successful: {tool_name}")
            self.statistics.record_success()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}", exc_info=True)
            self.statistics.record_failure()
            return {
                "success": False,
                "error": str(e)
            }


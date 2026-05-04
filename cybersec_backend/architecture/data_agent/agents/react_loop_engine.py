"""
ReAct Loop Engine

This module implements the ReAct (Reason-Act-Observe) pattern for agentic AI.
The ReAct loop is the core execution engine where:
1. OBSERVE: Get current system state
2. REASON: LLM reasons about the observation
3. ACT: Execute LLM's decided tool calls via MCP
4. OBSERVE: Feed tool results back to LLM
5. REPEAT: Continue the loop

Features:
- Reason-Act-Observe pattern implementation
- Tool execution via MCP clients
- Tool-to-server mapping for all 20 MCP tools
- Error handling with LLM feedback
- Configurable max iterations and sleep intervals
- Graceful shutdown support
- Comprehensive logging
"""

from typing import Dict, Any, List, Optional, Callable
import logging
import time
import json
from architecture.data_agent.agents.llm_reasoning_engine import LLMReasoningEngine
from architecture.data_agent.agents.mcp_client_factory import MCPClientFactory
from architecture.data_agent.agents.mcp_client import MCPClientError, MCPTimeoutError


class ReActLoopEngine:
    """
    ReAct Loop Engine for agentic AI agents.
    
    Implements the Reason-Act-Observe pattern where LLM serves as the
    agent's brain for decision-making. The loop continues until stopped
    or max iterations reached.
    
    Features:
    - Reason-Act-Observe loop execution
    - Tool execution via MCP clients
    - Tool-to-server mapping (20 tools across 4 servers)
    - Error handling with LLM feedback
    - Configurable iteration limits and sleep intervals
    - Graceful shutdown
    
    Requirements:
    - 2.1-2.10: ReAct pattern implementation
    
    Attributes:
        llm_engine: LLM reasoning engine for decision-making
        mcp_factory: MCP client factory for tool execution
        system_prompt: System prompt defining agent role
        available_tools: List of tools in OpenAI format
        max_iterations: Maximum loop iterations (0 = unlimited)
        sleep_seconds: Sleep between iterations
        running: Whether loop is currently running
        logger: Logger instance
    """
    
    # Tool-to-server mapping for all 21 MCP tools across 4 servers
    TOOL_SERVER_MAP = {
        # Collector-Executor MCP (11 tools)
        "collect_system_events": "collector_executor",
        "collect_file_events": "collector_executor",
        "collect_network_events": "collector_executor",
        "collect_process_events": "collector_executor",
        "collect_browser_events": "collector_executor",
        "collect_email_events": "collector_executor",
        "collect_windows_events": "collector_executor",
        "collect_usb_events": "collector_executor",
        "collect_clipboard_events": "collector_executor",
        "collect_registry_events": "collector_executor",
        "collect_dns_events": "collector_executor",
        
        # Event-Storage MCP (4 tools)
        "store_events": "event_storage",
        "query_events": "event_storage",
        "export_to_mailbox": "event_storage",
        "get_summary": "event_storage",
        
        # Attack-Injector MCP (3 tools)
        "list_attack_patterns": "attack_injector",
        "inject_attack": "attack_injector",
        "add_attack_pattern": "attack_injector",
        
        # Python-Executor MCP (2 tools)
        "execute_code": "python_executor",
        "list_allowed_imports": "python_executor",
    }
    
    def __init__(
        self,
        llm_engine: LLMReasoningEngine,
        mcp_factory: MCPClientFactory,
        system_prompt: str,
        available_tools: List[Dict[str, Any]],
        max_iterations: int = 0,
        sleep_seconds: float = 1.0,
        use_native_tool_calling: bool = False,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize ReAct Loop Engine.
        
        Args:
            llm_engine: LLM reasoning engine for decision-making
            mcp_factory: MCP client factory for tool execution
            system_prompt: System prompt defining agent role and capabilities
            available_tools: List of tools in OpenAI function calling format
            max_iterations: Maximum loop iterations (0 = unlimited, default: 0)
            sleep_seconds: Sleep between iterations (default: 1.0)
            use_native_tool_calling: Use native OpenAI tool calling (default: False)
            logger: Optional logger instance
        """
        self.llm_engine = llm_engine
        self.mcp_factory = mcp_factory
        self.system_prompt = system_prompt
        self.available_tools = available_tools
        self.max_iterations = max_iterations
        self.sleep_seconds = sleep_seconds
        self.use_native_tool_calling = use_native_tool_calling
        self.logger = logger or logging.getLogger("react_loop_engine")
        
        self.running = False
        self.iteration_count = 0
        
        self.logger.info("ReAct Loop Engine initialized")
        self.logger.info(f"Max iterations: {max_iterations if max_iterations > 0 else 'unlimited'}")
        self.logger.info(f"Sleep between iterations: {sleep_seconds}s")
        self.logger.info(f"Native tool calling: {use_native_tool_calling}")
        self.logger.info(f"Available tools: {len(available_tools)}")
    
    def run_loop(
        self,
        get_observation: Callable[[], str],
        on_iteration_complete: Optional[Callable[[int, Dict[str, Any]], None]] = None
    ):
        """
        Run the ReAct (Reason-Act-Observe) loop.
        
        The loop follows this pattern:
        1. OBSERVE: Get current system state via get_observation()
        2. REASON: Ask LLM to reason about observation
        3. ACT: Execute LLM's decided tool calls via MCP
        4. OBSERVE: Feed tool results back to LLM
        5. REPEAT: Continue until stopped or max iterations
        
        Args:
            get_observation: Callable that returns current system state as string
            on_iteration_complete: Optional callback after each iteration
                                  Called with (iteration_number, iteration_results)
        
        Requirements:
        - 2.1: Implement Reason-Act-Observe pattern
        - 2.2: Get current observation (system state)
        - 2.3: Ask LLM to reason about observation
        - 2.4: Execute LLM's decided tool calls via MCP
        - 2.5: Feed tool results back to LLM
        - 2.6: Continue loop until stopped or max iterations
        - 2.9: Support configurable sleep between iterations
        - 2.10: Log all LLM reasoning and tool executions
        """
        self.logger.info("🚀 Starting adversarial agent ReAct loop...")
        self.running = True
        self.iteration_count = 0
        
        try:
            while self.running:
                # Check iteration limit
                if self.max_iterations > 0 and self.iteration_count >= self.max_iterations:
                    self.logger.info(f"🏁 Reached max iterations: {self.max_iterations}")
                    break
                
                self.iteration_count += 1
                self.logger.info(f"🔄 === Iteration {self.iteration_count} ===")
                
                iteration_start_time = time.time()
                iteration_results = {
                    "iteration": self.iteration_count,
                    "observation": None,
                    "reasoning": None,
                    "tool_calls": [],
                    "tool_results": [],
                    "errors": [],
                    "duration_seconds": 0
                }
                
                try:
                    # STEP 1: OBSERVE - Get current system state
                    self.logger.info("🤖 Agent observing system state...")
                    observation = get_observation()
                    iteration_results["observation"] = observation[:200] + "..." if len(observation) > 200 else observation
                    self.logger.debug(f"Observation: {observation[:500]}...")
                    
                    # STEP 2: REASON - Ask LLM to reason about observation
                    self.logger.info("🧠 LLM analyzing current state...")
                    llm_response = self.llm_engine.reason(
                        system_prompt=self.system_prompt,
                        observation=observation,
                        available_tools=self.available_tools,
                        use_native_tool_calling=self.use_native_tool_calling
                    )
                    
                    iteration_results["reasoning"] = llm_response.get("reasoning", "")
                    tool_calls = llm_response.get("tool_calls", [])
                    
                    self.logger.info(f"💭 LLM Reasoning: {llm_response.get('reasoning', '')}")
                    self.logger.info(f"🎯 LLM decided to call {len(tool_calls)} tool(s)")
                    
                    # STEP 3: ACT - Execute LLM's decided tool calls via MCP
                    if tool_calls:
                        self.logger.info(f"⚙️ Executing {len(tool_calls)} tool call(s)...")
                        
                        for tool_call in tool_calls:
                            tool_call_id = tool_call.get("id", "unknown")
                            tool_name = tool_call.get("name", "unknown")
                            tool_arguments = tool_call.get("arguments", {})
                            
                            self.logger.info(f"🔧 Executing tool: {tool_name}")
                            
                            try:
                                # Execute tool via MCP
                                tool_result = self._execute_mcp_tool(tool_name, tool_arguments)
                                
                                iteration_results["tool_calls"].append({
                                    "id": tool_call_id,
                                    "name": tool_name,
                                    "arguments": tool_arguments,
                                    "success": True
                                })
                                iteration_results["tool_results"].append({
                                    "id": tool_call_id,
                                    "name": tool_name,
                                    "result": tool_result
                                })
                                
                                self.logger.info(f"✓ {tool_name} executed successfully")
                                self.logger.debug(f"Tool result: {json.dumps(tool_result, indent=2)[:500]}...")
                                
                                # STEP 4: OBSERVE - Feed tool result back to LLM
                                self.logger.info(f"📥 Feeding tool result back to LLM")
                                self.llm_engine.add_tool_result(
                                    tool_call_id=tool_call_id,
                                    tool_name=tool_name,
                                    result=tool_result
                                )
                            
                            except Exception as e:
                                # Handle tool execution error
                                error_msg = f"Tool {tool_name} failed: {str(e)}"
                                self.logger.error(f"✗ {error_msg}", exc_info=True)
                                
                                iteration_results["tool_calls"].append({
                                    "id": tool_call_id,
                                    "name": tool_name,
                                    "arguments": tool_arguments,
                                    "success": False,
                                    "error": str(e)
                                })
                                iteration_results["errors"].append(error_msg)
                                
                                # Feed error to LLM for adaptive recovery
                                error_result = {
                                    "error": str(e),
                                    "error_type": type(e).__name__,
                                    "tool_name": tool_name,
                                    "message": "Tool execution failed. Consider alternative approaches."
                                }
                                
                                self.logger.info("⚠️ Feeding error to LLM for adaptive recovery")
                                self.llm_engine.add_tool_result(
                                    tool_call_id=tool_call_id,
                                    tool_name=tool_name,
                                    result=error_result
                                )
                    else:
                        self.logger.info("⏭️ No tool calls decided by LLM")
                    
                    # Calculate iteration duration
                    iteration_results["duration_seconds"] = time.time() - iteration_start_time
                    
                    # Call iteration complete callback
                    if on_iteration_complete:
                        try:
                            on_iteration_complete(self.iteration_count, iteration_results)
                        except Exception as e:
                            self.logger.error(f"Error in iteration callback: {e}", exc_info=True)
                    
                    # Log iteration summary
                    tool_calls_list = iteration_results.get("tool_calls", [])
                    successful_calls = sum(1 for tc in tool_calls_list if tc.get("success", False))
                    failed_calls = sum(1 for tc in tool_calls_list if not tc.get("success", True))
                    
                    self.logger.info(
                        f"✅ Iteration {self.iteration_count} complete: "
                        f"{successful_calls} tools succeeded, {failed_calls} tools failed, "
                        f"duration: {iteration_results.get('duration_seconds', 0):.2f}s"
                    )
                    
                    # STEP 5: REPEAT - Sleep before next iteration (only if sleep_seconds > 0)
                    if self.running and (self.max_iterations == 0 or self.iteration_count < self.max_iterations):
                        if self.sleep_seconds > 0:
                            self.logger.info(f"⏳ Sleeping {self.sleep_seconds}s before next iteration")
                            time.sleep(self.sleep_seconds)
                        # If sleep_seconds is 0, continue immediately to next iteration
                
                except Exception as e:
                    self.logger.error(f"Error in ReAct loop iteration {self.iteration_count}: {e}", exc_info=True)
                    iteration_results["errors"].append(str(e))
                    iteration_results["duration_seconds"] = time.time() - iteration_start_time
                    
                    # Brief pause before retry
                    time.sleep(2)
        
        finally:
            self.running = False
            self.logger.info(f"ReAct loop stopped after {self.iteration_count} iterations")
    
    def _execute_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute an MCP tool by mapping tool name to appropriate server.
        
        Uses TOOL_SERVER_MAP to route tool calls to the correct MCP server:
        - collector_executor: 11 collector tools
        - event_storage: 4 storage/query tools
        - attack_injector: 3 attack simulation tools
        - python_executor: 2 code execution tools
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
        
        Returns:
            Tool execution result
        
        Raises:
            ValueError: If tool name is not in TOOL_SERVER_MAP
            MCPClientError: If tool execution fails
            MCPTimeoutError: If tool execution times out
        
        Requirements:
        - 2.4: Execute LLM's decided tool calls via MCP
        - 2.7: Handle tool execution errors gracefully
        - 2.8: Feed errors to LLM for adaptive recovery
        """
        # Map tool to server
        if tool_name not in self.TOOL_SERVER_MAP:
            raise ValueError(f"Unknown tool: {tool_name}. Not in TOOL_SERVER_MAP.")
        
        server_name = self.TOOL_SERVER_MAP[tool_name]
        self.logger.debug(f"Routing tool {tool_name} to server {server_name}")
        
        # Get MCP client for server
        try:
            client = self.mcp_factory.get_client(server_name)
        except Exception as e:
            raise MCPClientError(f"Failed to get MCP client for {server_name}: {e}")
        
        # Execute tool with configured timeout
        try:
            # Special case: browser and email collectors get shorter timeout (45s instead of 180s)
            if tool_name in ["collect_browser_events", "collect_email_events"]:
                timeout = 45  # Shorter timeout for browser and email collectors
            else:
                timeout = client.request_timeout  # Use configured timeout for other tools
            
            result = client.call_tool(tool_name, arguments, timeout=timeout)
            return result
        except MCPTimeoutError as e:
            self.logger.error(f"Tool {tool_name} timed out: {e}")
            raise
        except MCPClientError as e:
            self.logger.error(f"Tool {tool_name} failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error executing tool {tool_name}: {e}", exc_info=True)
            raise MCPClientError(f"Tool execution failed: {e}")
    
    def stop(self):
        """
        Stop the ReAct loop gracefully.
        
        Sets running flag to False, causing the loop to exit after
        the current iteration completes.
        
        Requirements:
        - 2.6: Support graceful shutdown
        """
        self.logger.info("Stopping ReAct loop")
        self.running = False
    
    def is_running(self) -> bool:
        """
        Check if ReAct loop is currently running.
        
        Returns:
            True if loop is running, False otherwise
        """
        return self.running
    
    def get_iteration_count(self) -> int:
        """
        Get current iteration count.
        
        Returns:
            Number of iterations completed
        """
        return self.iteration_count
    
    def set_max_iterations(self, max_iterations: int):
        """
        Update maximum iterations limit.
        
        Args:
            max_iterations: New max iterations (0 = unlimited)
        """
        if max_iterations < 0:
            raise ValueError("max_iterations must be non-negative")
        
        self.logger.info(f"Updating max_iterations from {self.max_iterations} to {max_iterations}")
        self.max_iterations = max_iterations
    
    def set_sleep_seconds(self, sleep_seconds: float):
        """
        Update sleep interval between iterations.
        
        Args:
            sleep_seconds: New sleep interval in seconds
        """
        if sleep_seconds < 0:
            raise ValueError("sleep_seconds must be non-negative")
        
        self.logger.info(f"Updating sleep_seconds from {self.sleep_seconds} to {sleep_seconds}")
        self.sleep_seconds = sleep_seconds
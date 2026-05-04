"""
LLM Reasoning Engine

This module provides the LLMReasoningEngine class that interfaces with
LLM (Llama 3.1 70B) via OpenAI-compatible API for agent decision-making.

Features:
- OpenAI client with custom base_url and SSL verification control
- Tool calling (function calling) support for MCP tool invocation
- Conversation history management (last 20 messages)
- Configurable temperature and max_tokens
- Graceful error handling for LLM API failures
- Comprehensive logging of all LLM interactions
- Configuration loading from agents/config.json with env var overrides
"""

from typing import Dict, Any, List, Optional
import logging
from openai import OpenAI
import json
import httpx
from architecture.data_agent.agents.llm_config import load_llm_config, LLMConfig


class LLMReasoningEngine:
    """
    LLM Reasoning Engine for agentic AI decision-making.
    
    This class serves as the "brain" of agentic AI agents, using LLM
    to reason about observations, decide which tools to use, and adapt
    to changing conditions.
    
    Features:
    - Connects to Llama 3.1 70B via OpenAI-compatible API
    - Maintains conversation history for context
    - Supports tool calling (function calling) format
    - Handles LLM API errors gracefully
    - Logs all interactions for debugging
    
    Attributes:
        client: OpenAI client instance
        model: LLM model name
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens in response
        conversation_history: List of messages (last 20)
        logger: Logger instance
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        verify_ssl: bool = False,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize LLM Reasoning Engine.
        
        Args:
            api_key: API key for LLM service
            base_url: Base URL for LLM API endpoint
            model: Model name (e.g., "hosted_vllm/Llama-3.1-70B-Instruct")
            temperature: Sampling temperature (0.0-1.0, default: 0.7)
            max_tokens: Maximum tokens in response (default: 2000)
            verify_ssl: Whether to verify SSL certificates (default: False for university proxy)
            logger: Optional logger instance
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.logger = logger or logging.getLogger("llm_reasoning_engine")
        
        # Initialize conversation history (last 20 messages)
        self.conversation_history: List[Dict[str, Any]] = []
        self.max_history_length = 20
        
        # Create HTTP client with SSL verification control
        http_client = httpx.Client(verify=verify_ssl)
        
        # Initialize OpenAI client with custom base_url
        try:
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=http_client
            )
            self.logger.info(f"LLM Reasoning Engine initialized with model: {model}")
            self.logger.info(f"Base URL: {base_url}, SSL verification: {verify_ssl}")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
            raise
    
    @classmethod
    def from_config(cls, config: Optional[LLMConfig] = None, logger: Optional[logging.Logger] = None):
        """
        Create LLM Reasoning Engine from configuration.
        
        This is the recommended way to create an instance, as it handles
        configuration loading from agents/config.json with environment
        variable overrides.
        
        Args:
            config: Optional LLMConfig instance (loads from file if None)
            logger: Optional logger instance
        
        Returns:
            LLMReasoningEngine instance
        
        Example:
            >>> engine = LLMReasoningEngine.from_config()
            >>> result = engine.reason(system_prompt, observation, tools)
        """
        if config is None:
            config = load_llm_config(logger=logger)
        
        return cls(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            verify_ssl=config.verify_ssl,
            logger=logger
        )
    
    def reason(
        self,
        system_prompt: str,
        observation: str,
        available_tools: Optional[List[Dict[str, Any]]] = None,
        use_native_tool_calling: bool = False
    ) -> Dict[str, Any]:
        """
        Ask LLM to reason about an observation and decide actions.
        
        This is the core method where LLM acts as the agent's brain:
        1. Receives system prompt (defines agent role)
        2. Receives observation (current system state)
        3. Receives available tools (MCP tools LLM can use)
        4. Returns LLM's reasoning and decided tool calls
        
        Supports two modes:
        - Native tool calling (OpenAI format) - requires LLM support
        - Prompt-based tool calling (JSON in response) - works with any LLM
        
        Args:
            system_prompt: Instructions defining agent role and capabilities
            observation: Current system state for LLM to reason about
            available_tools: List of tools in OpenAI function calling format
            use_native_tool_calling: If True, use OpenAI tool calling format.
                                    If False (default), use prompt-based approach.
        
        Returns:
            Dictionary containing:
            - reasoning: LLM's reasoning text (if provided)
            - tool_calls: List of tool calls LLM decided to make
            - finish_reason: Why LLM stopped (e.g., "tool_calls", "stop")
        
        Raises:
            Exception: If LLM API call fails
        """
        self.logger.info("LLM reasoning requested")
        self.logger.debug(f"Observation: {observation[:200]}...")  # Log first 200 chars
        
        try:
            # Prepare observation with tool instructions if tools provided
            if available_tools and not use_native_tool_calling:
                # Prompt-based approach: Add tool descriptions to observation
                observation = self._format_observation_with_tools(observation, available_tools)
            
            # Add observation to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": observation
            })
            
            # Prepare messages (system prompt + conversation history)
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(self.conversation_history)
            
            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            # Add tools if using native tool calling
            if available_tools and use_native_tool_calling:
                api_params["tools"] = available_tools
                api_params["tool_choice"] = "auto"
                self.logger.debug(f"Using native tool calling with {len(available_tools)} tools")
            elif available_tools:
                self.logger.debug(f"Using prompt-based tool calling with {len(available_tools)} tools")
            
            # Call LLM API
            self.logger.debug(f"Calling LLM API with {len(messages)} messages")
            response = self.client.chat.completions.create(**api_params)
            
            # Extract response
            message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
            
            # Log token usage if available
            if hasattr(response, 'usage') and response.usage:
                self.logger.info(
                    f"Token usage - Prompt: {response.usage.prompt_tokens}, "
                    f"Completion: {response.usage.completion_tokens}, "
                    f"Total: {response.usage.total_tokens}"
                )
            
            # Add assistant response to conversation history
            assistant_message = {"role": "assistant"}
            if message.content:
                assistant_message["content"] = message.content
            if hasattr(message, 'tool_calls') and message.tool_calls:
                assistant_message["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            
            self.conversation_history.append(assistant_message)
            
            # Trim conversation history to last 20 messages
            if len(self.conversation_history) > self.max_history_length:
                self.conversation_history = self.conversation_history[-self.max_history_length:]
                self.logger.debug(f"Trimmed conversation history to {self.max_history_length} messages")
            
            # Prepare result
            result = {
                "reasoning": message.content or "",
                "tool_calls": [],
                "finish_reason": finish_reason
            }
            
            # Parse tool calls - native format or prompt-based
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # Native tool calling format
                for tool_call in message.tool_calls:
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                        result["tool_calls"].append({
                            "id": tool_call.id,
                            "name": tool_call.function.name,
                            "arguments": arguments
                        })
                        self.logger.info(f"LLM decided to call tool: {tool_call.function.name}")
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse tool arguments: {e}")
            elif available_tools and not use_native_tool_calling:
                # Prompt-based tool calling - parse JSON from response
                tool_calls = self._parse_tool_calls_from_text(message.content or "")
                result["tool_calls"] = tool_calls
                
                # Extract reasoning from JSON response
                reasoning_text = self._extract_reasoning_from_text(message.content or "")
                if reasoning_text:
                    result["reasoning"] = reasoning_text
                
                if tool_calls:
                    self.logger.info(f"Parsed {len(tool_calls)} tool calls from LLM response")
            
            # Log reasoning
            if result["reasoning"]:
                self.logger.info(f"LLM reasoning: {result['reasoning']}")
            
            self.logger.info(f"LLM reasoning completed (finish_reason: {finish_reason})")
            return result
        
        except Exception as e:
            self.logger.error(f"LLM API error: {e}", exc_info=True)
            raise
    
    def _format_observation_with_tools(self, observation: str, tools: List[Dict[str, Any]]) -> str:
        """
        Format observation with tool descriptions for prompt-based tool calling.
        
        Args:
            observation: Original observation text
            tools: List of available tools in OpenAI format
        
        Returns:
            Enhanced observation with tool instructions
        """
        tool_descriptions = []
        for tool in tools:
            func = tool.get("function", {})
            name = func.get("name", "unknown")
            description = func.get("description", "No description")
            params = func.get("parameters", {}).get("properties", {})
            required = func.get("parameters", {}).get("required", [])
            
            param_desc = []
            for param_name, param_info in params.items():
                param_type = param_info.get("type", "any")
                param_desc_text = param_info.get("description", "")
                is_required = " (required)" if param_name in required else " (optional)"
                param_desc.append(f"  - {param_name} ({param_type}){is_required}: {param_desc_text}")
            
            tool_desc = f"- {name}: {description}"
            if param_desc:
                tool_desc += "\n" + "\n".join(param_desc)
            tool_descriptions.append(tool_desc)
        
        tools_text = "\n".join(tool_descriptions)
        
        enhanced_observation = f"""{observation}

AVAILABLE TOOLS:
{tools_text}

INSTRUCTIONS FOR TOOL CALLING:
You MUST respond with a valid JSON object. Follow this EXACT format:

{{
  "reasoning": "Your reasoning about what to do and why",
  "tool_calls": [
    {{
      "name": "tool_name",
      "arguments": {{"param1": "value1", "param2": 123}}
    }}
  ]
}}

CRITICAL JSON RULES:
1. Use double quotes (") for all strings, NOT single quotes (')
2. Do NOT use trailing commas before closing braces or brackets
3. String values must be in double quotes: "value"
4. Number values should NOT be in quotes: 123
5. Boolean values: true or false (lowercase, no quotes)
6. Ensure all braces and brackets are properly matched

EXAMPLES:
- Correct: {{"name": "collect_system_events", "arguments": {{}}}}
- Correct: {{"name": "collect_browser_events", "arguments": {{"hours_back": 24}}}}
- WRONG: {{'name': 'tool'}} (single quotes)
- WRONG: {{"name": "tool",}} (trailing comma)

If you don't need to use any tools, respond with:
{{
  "reasoning": "Your reasoning here"
}}

You can call multiple tools by including multiple objects in the tool_calls array.
"""
        return enhanced_observation
    
    def _parse_tool_calls_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse tool calls from LLM response text (prompt-based approach).
        
        Looks for JSON objects with tool_calls in the response.
        
        Args:
            text: LLM response text
        
        Returns:
            List of tool calls with id, name, and arguments
        """
        tool_calls = []
        
        try:
            # Try to find JSON in the response
            # Look for JSON code blocks first
            import re
            
            # Strategy 1: Look for JSON code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # Strategy 2: Try to find raw JSON object with proper brace matching
                # Find the first { and match it with the corresponding }
                start_idx = text.find('{')
                if start_idx != -1:
                    brace_count = 0
                    end_idx = start_idx
                    for i in range(start_idx, len(text)):
                        if text[i] == '{':
                            brace_count += 1
                        elif text[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break
                    
                    if end_idx > start_idx:
                        json_text = text[start_idx:end_idx]
                    else:
                        # No matching closing brace found
                        self.logger.warning("No matching closing brace found in LLM response")
                        return []
                else:
                    # No JSON found
                    self.logger.debug("No JSON object found in LLM response")
                    return []
            
            # Clean up common JSON issues before parsing
            # Remove trailing commas before closing braces/brackets
            json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
            
            # Sanitize control characters that LLMs often include in JSON strings
            # JSON standard forbids literal control chars (\x00-\x1f) inside strings;
            # they must be escaped (e.g. \n not a real newline). LLMs often return
            # literal newlines/tabs in their reasoning text, breaking json.loads().
            json_text = re.sub(r'[\x00-\x1f\x7f]', ' ', json_text)
            
            # Try to parse JSON
            try:
                parsed = json.loads(json_text)
            except json.JSONDecodeError as e:
                # Log the problematic JSON for debugging
                self.logger.warning(f"Failed to parse JSON from LLM response: {e}")
                self.logger.debug(f"Problematic JSON text: {json_text[:500]}...")
                
                # Try to fix common issues and parse again
                # Fix single quotes to double quotes
                json_text_fixed = json_text.replace("'", '"')
                try:
                    parsed = json.loads(json_text_fixed)
                    self.logger.info("Successfully parsed JSON after fixing quotes")
                except json.JSONDecodeError:
                    # Give up
                    return []
            
            # Extract tool calls
            if "tool_calls" in parsed and isinstance(parsed["tool_calls"], list):
                for i, tc in enumerate(parsed["tool_calls"]):
                    if isinstance(tc, dict) and "name" in tc:
                        tool_calls.append({
                            "id": f"call_{i}_{tc['name']}",
                            "name": tc["name"],
                            "arguments": tc.get("arguments", {})
                        })
                        self.logger.info(f"Parsed tool call: {tc['name']}")
            else:
                self.logger.debug("No tool_calls field found in parsed JSON")
        
        except Exception as e:
            self.logger.warning(f"Error parsing tool calls: {e}", exc_info=True)
        
        return tool_calls
    
    def _extract_reasoning_from_text(self, text: str) -> str:
        """
        Extract reasoning text from LLM response (prompt-based approach).
        
        Extracts the 'reasoning' field from JSON response.
        
        Args:
            text: LLM response text
        
        Returns:
            Reasoning text or empty string
        """
        try:
            import re
            
            # Try to find JSON in the response
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # Try to find raw JSON object
                start_idx = text.find('{')
                if start_idx != -1:
                    brace_count = 0
                    end_idx = start_idx
                    for i in range(start_idx, len(text)):
                        if text[i] == '{':
                            brace_count += 1
                        elif text[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break
                    
                    if end_idx > start_idx:
                        json_text = text[start_idx:end_idx]
                    else:
                        return ""
                else:
                    return ""
            
            # Clean up JSON
            json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
            
            # Sanitize control characters (literal newlines/tabs from LLM)
            json_text = re.sub(r'[\x00-\x1f\x7f]', ' ', json_text)
            
            # Parse JSON
            try:
                parsed = json.loads(json_text)
            except json.JSONDecodeError:
                # Try fixing quotes
                json_text_fixed = json_text.replace("'", '"')
                try:
                    parsed = json.loads(json_text_fixed)
                except json.JSONDecodeError:
                    return ""
            
            # Extract reasoning
            if "reasoning" in parsed and isinstance(parsed["reasoning"], str):
                return parsed["reasoning"]
        
        except Exception as e:
            self.logger.debug(f"Error extracting reasoning: {e}")
        
        return ""
    
    def add_tool_result(self, tool_call_id: str, tool_name: str, result: Any):
        """
        Add tool execution result to conversation history.
        
        This feeds tool results back to LLM so it can learn from
        the outcomes of its decisions and adapt accordingly.
        
        Args:
            tool_call_id: ID of the tool call (from LLM response)
            tool_name: Name of the tool that was executed
            result: Tool execution result (will be JSON serialized)
        """
        self.logger.debug(f"Adding tool result for {tool_name} (id: {tool_call_id})")
        
        try:
            # Serialize result to JSON string
            result_str = json.dumps(result, indent=2)
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "content": result_str
            })
            
            # Trim history if needed
            if len(self.conversation_history) > self.max_history_length:
                self.conversation_history = self.conversation_history[-self.max_history_length:]
            
            self.logger.debug(f"Tool result added (length: {len(result_str)} chars)")
        
        except Exception as e:
            self.logger.error(f"Failed to add tool result: {e}", exc_info=True)
    
    def clear_history(self):
        """
        Clear conversation history.
        
        Use this to reset LLM context when starting a new task
        or when conversation history becomes too long/irrelevant.
        """
        self.logger.info("Clearing conversation history")
        history_length = len(self.conversation_history)
        self.conversation_history.clear()
        self.logger.debug(f"Cleared {history_length} messages from history")
    
    def get_history_length(self) -> int:
        """
        Get current conversation history length.
        
        Returns:
            Number of messages in conversation history
        """
        return len(self.conversation_history)
    
    def set_temperature(self, temperature: float):
        """
        Update sampling temperature.
        
        Args:
            temperature: New temperature value (0.0-1.0)
        """
        if not 0.0 <= temperature <= 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")
        
        self.logger.info(f"Updating temperature from {self.temperature} to {temperature}")
        self.temperature = temperature
    
    def set_max_tokens(self, max_tokens: int):
        """
        Update maximum tokens in response.
        
        Args:
            max_tokens: New max_tokens value
        """
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        
        self.logger.info(f"Updating max_tokens from {self.max_tokens} to {max_tokens}")
        self.max_tokens = max_tokens

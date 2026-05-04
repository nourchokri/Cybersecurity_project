"""
Phase 3: Autonomous AI Agents

This package contains autonomous agents that interact with Phase 2 MCP servers
to perform continuous data collection, processing, and attack simulation.
"""

from .agent_state import AgentState, AgentStatistics
from .base_agent import BaseAgent
from .llm_reasoning_engine import LLMReasoningEngine
from .react_loop_engine import ReActLoopEngine
from .mcp_client_factory import MCPClientFactory
from .llm_data_engineering_agent import LLMDataEngineeringAgent

__version__ = "1.0.0"

__all__ = [
    "AgentState",
    "AgentStatistics",
    "BaseAgent",
    "LLMReasoningEngine",
    "ReActLoopEngine",
    "MCPClientFactory",
    "LLMDataEngineeringAgent",
]

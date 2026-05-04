"""
LangGraph graph assembly for Behavior Agent.
Uses MemorySaver for persistent memory — no RAM growth during long sessions.
"""
import logging
from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import (
    node_load_baseline,
    node_score_session,
    node_update_baseline,
    node_generate_explanation,
    node_build_result,
)
from ..memory.checkpointer import get_checkpointer

logger = logging.getLogger('behavior_agent')


def build_graph():
    g = StateGraph(AgentState)

    g.add_node('load_baseline',        node_load_baseline)
    g.add_node('score_session',        node_score_session)
    g.add_node('update_baseline',      node_update_baseline)
    g.add_node('generate_explanation', node_generate_explanation)
    g.add_node('build_result',         node_build_result)

    g.set_entry_point('load_baseline')
    g.add_edge('load_baseline',        'score_session')
    g.add_edge('score_session',        'update_baseline')
    g.add_edge('update_baseline',      'generate_explanation')
    g.add_edge('generate_explanation', 'build_result')
    g.add_edge('build_result',         END)

    # MemorySaver: persistent memory, no RAM growth
    checkpointer = get_checkpointer()
    compiled = g.compile(checkpointer=checkpointer)
    logger.info('LangGraph graph compiled with MemorySaver checkpointer')
    return compiled


# Singleton — built once, reused for all invocations
graph = build_graph()
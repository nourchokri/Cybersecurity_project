"""
LangGraph AgentState definition.
Single source of truth for the state schema used across all nodes.
"""
from typing import TypedDict, Optional


class AgentState(TypedDict):
    session:          dict            # closed session dict from test_sessions.parquet
    baseline:         Optional[dict]  # serialized UserBaseline fields
    features:         Optional[dict]  # 18-feature vector
    if_score:         Optional[float] # raw IF model score [0,1]
    dim_scores:       Optional[dict]  # {time, device, volume, sensitivity}
    final_score:      Optional[float] # final anomaly score (IF-only mode)
    triggered_rules:  Optional[list]  # list of rule name strings
    explanation:      Optional[str]   # LLM or template explanation
    anomaly_result:   Optional[dict]  # full AnomalyResult (Contract 3)
    error:            Optional[str]   # set if any node fails
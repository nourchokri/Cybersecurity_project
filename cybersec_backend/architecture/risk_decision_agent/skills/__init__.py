"""
Skills package for the Risk & Decision Agent.

Skills are internal cognitive capabilities that enable the agent to:
- Compute risk deterministically (no LLM math errors)
"""

from .risk_computation import RiskComputationSkill

__all__ = ["RiskComputationSkill"]

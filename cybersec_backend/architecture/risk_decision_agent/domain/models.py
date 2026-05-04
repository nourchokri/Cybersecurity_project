"""
Internal data structures for the risk_decision_agent domain.

These are plain Python dataclasses — NOT Django ORM models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AnomalyEvent:
    """Incoming event from Team 2 (Pattern Agent)."""

    event_id: str
    user_id: str
    entity_id: str = ""
    timestamp: str = ""
    score: float = 0.0
    if_score: Optional[float] = None
    dim_scores: Optional[Dict[str, float]] = None
    triggered_rules: List[str] = field(default_factory=list)
    raw_features: Optional[Dict[str, Any]] = None
    confidence: str = "medium"
    cold_start: bool = False
    threat_classification: str = "unknown"
    monitor: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "user_id": self.user_id,
            "entity_id": self.entity_id,
            "timestamp": self.timestamp,
            "score": self.score,
            "if_score": self.if_score,
            "dim_scores": self.dim_scores,
            "triggered_rules": self.triggered_rules,
            "raw_features": self.raw_features,
            "confidence": self.confidence,
            "cold_start": self.cold_start,
            "threat_classification": self.threat_classification,
            "monitor": self.monitor,
        }


@dataclass
class DecisionResult:
    """Output decision for Team 4 (Reporting Agent)."""

    event_id: str
    user_id: str
    base_score: float
    risk_adjustment: float
    adjusted_risk_score: float
    risk_level: str  # LOW | MEDIUM | HIGH
    decision: str  # ALLOW | MONITOR | ESCALATE | BLOCK
    recommended_action: str
    confidence: str
    risk_factors: List[str] = field(default_factory=list)
    mitigating_factors: List[str] = field(default_factory=list)
    base_score_analysis: str = ""
    adjustment_reasoning: str = ""
    decision_reasoning: str = ""
    context_summary: Dict[str, Any] = field(default_factory=dict)

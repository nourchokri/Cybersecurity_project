"""Data models for Response Agent."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class RiskAgentOutput:
    """Input from Risk Decision Agent."""
    event_id: str
    timestamp: str
    user_id: str
    entity_id: str
    base_score: float
    risk_adjustment: float
    adjusted_risk_score: float
    risk_level: str  # LOW | MEDIUM | HIGH
    decision: str  # ALLOW | MONITOR | ESCALATE | BLOCK
    recommended_action: str
    risk_factors: List[str]
    mitigating_factors: List[str]
    context_summary: Dict[str, Any]
    confidence: str
    computation_method: str
    llm_driven: bool
    execution_logs: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RiskAgentOutput:
        return cls(
            event_id=data.get("event_id", ""),
            timestamp=data.get("timestamp", ""),
            user_id=data.get("user_id", ""),
            entity_id=data.get("entity_id", ""),
            base_score=data.get("base_score", 0.0),
            risk_adjustment=data.get("risk_adjustment", 0.0),
            adjusted_risk_score=data.get("adjusted_risk_score", 0.0),
            risk_level=data.get("risk_level", "UNKNOWN"),
            decision=data.get("decision", "UNKNOWN"),
            recommended_action=data.get("recommended_action", ""),
            risk_factors=data.get("risk_factors", []),
            mitigating_factors=data.get("mitigating_factors", []),
            context_summary=data.get("context_summary", {}),
            confidence=data.get("confidence", "medium"),
            computation_method=data.get("computation_method", "unknown"),
            llm_driven=data.get("llm_driven", False),
            execution_logs=data.get("execution_logs", [])
        )


@dataclass
class FeatureWeights:
    """LLM-generated feature weights."""
    base_score_weight: float
    risk_factors_weight: float
    mitigating_factors_weight: float
    context_weight: float
    confidence_weight: float
    reasoning: str


@dataclass
class DecisionOutput:
    """Output from a decision component."""
    action: str  # ALLOW | BLOCK | ESCALATE | MONITOR
    confidence: float
    reasoning: str
    source: str  # llm_weighted | llm_direct | rl_model


@dataclass
class FinalDecision:
    """Final orchestrated decision."""
    event_id: str
    user_id: str
    timestamp: str
    risk_level: str
    final_action: str  # ALLOW | BLOCK | ESCALATE | MONITOR
    execution_status: str  # AUTO_EXECUTED | PENDING_USER | LOGGED
    
    # Decision components
    llm_weighted_decision: DecisionOutput
    llm_direct_decision: DecisionOutput
    rl_decision: DecisionOutput
    
    # Orchestration
    orchestrator_reasoning: str
    confidence: float
    
    # Explanation
    risk_explanation: str
    action_explanation: str
    
    # User interaction (for MEDIUM risk)
    user_approval_required: bool = False
    user_approval_status: Optional[str] = None  # APPROVED | DENIED | TIMEOUT
    twilio_call_sid: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "risk_level": self.risk_level,
            "final_action": self.final_action,
            "execution_status": self.execution_status,
            "llm_weighted_decision": {
                "action": self.llm_weighted_decision.action,
                "confidence": self.llm_weighted_decision.confidence,
                "reasoning": self.llm_weighted_decision.reasoning,
                "source": self.llm_weighted_decision.source
            },
            "llm_direct_decision": {
                "action": self.llm_direct_decision.action,
                "confidence": self.llm_direct_decision.confidence,
                "reasoning": self.llm_direct_decision.reasoning,
                "source": self.llm_direct_decision.source
            },
            "rl_decision": {
                "action": self.rl_decision.action,
                "confidence": self.rl_decision.confidence,
                "reasoning": self.rl_decision.reasoning,
                "source": self.rl_decision.source
            },
            "orchestrator_reasoning": self.orchestrator_reasoning,
            "confidence": self.confidence,
            "risk_explanation": self.risk_explanation,
            "action_explanation": self.action_explanation,
            "user_approval_required": self.user_approval_required,
            "user_approval_status": self.user_approval_status,
            "twilio_call_sid": self.twilio_call_sid
        }


@dataclass
class RLTrainingData:
    """Training data for RL model."""
    event_id: str
    features: Dict[str, float]
    action_taken: str
    outcome: str  # SUCCESS | FALSE_POSITIVE | FALSE_NEGATIVE | INCIDENT
    reward: float
    timestamp: str

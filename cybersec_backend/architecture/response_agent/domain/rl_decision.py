"""RL-based decision making."""

from __future__ import annotations
import logging
from ..infrastructure.rl_model import RLModelManager
from .models import RiskAgentOutput, DecisionOutput

logger = logging.getLogger(__name__)


class RLDecisionMaker:
    """Uses RL model to make decisions."""
    
    def __init__(self):
        self.rl_manager = RLModelManager()
    
    def _extract_features(self, risk_output: RiskAgentOutput) -> dict:
        """Extract features for RL model."""
        # Map risk level to numeric
        risk_level_map = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
        
        return {
            "adjusted_risk_score": risk_output.adjusted_risk_score,
            "base_score": risk_output.base_score,
            "risk_level_numeric": risk_level_map.get(risk_output.risk_level, 1),
            "risk_factors_count": len(risk_output.risk_factors),
            "mitigating_factors_count": len(risk_output.mitigating_factors),
            "risk_adjustment": risk_output.risk_adjustment,
            "confidence_numeric": {"low": 0.33, "medium": 0.66, "high": 1.0}.get(risk_output.confidence, 0.66)
        }
    
    def decide(self, risk_output: RiskAgentOutput) -> DecisionOutput:
        """Make decision using RL model."""
        try:
            features = self._extract_features(risk_output)
            action, confidence = self.rl_manager.predict(features)
            
            reasoning = f"""
RL Model Decision:
- Predicted action: {action}
- Model confidence: {confidence:.3f}
- Features used:
  * Adjusted risk score: {features['adjusted_risk_score']:.3f}
  * Risk level: {risk_output.risk_level}
  * Risk factors: {features['risk_factors_count']}
  * Mitigating factors: {features['mitigating_factors_count']}
  
Model stats: {self.rl_manager.get_stats()}
"""
            
            return DecisionOutput(
                action=action,
                confidence=confidence,
                reasoning=reasoning.strip(),
                source="rl_model"
            )
            
        except Exception as e:
            logger.error(f"RL decision failed: {e}")
            # Fallback to simple rule-based
            if risk_output.adjusted_risk_score >= 0.7:
                action = "BLOCK"
            elif risk_output.adjusted_risk_score >= 0.5:
                action = "ESCALATE"
            elif risk_output.adjusted_risk_score >= 0.3:
                action = "MONITOR"
            else:
                action = "ALLOW"
            
            return DecisionOutput(
                action=action,
                confidence=0.5,
                reasoning=f"Fallback rule-based decision due to RL error: {e}",
                source="rl_model"
            )
    
    def train_from_feedback(self, risk_output: RiskAgentOutput, action_taken: str, 
                           outcome: str) -> None:
        """Train RL model from user feedback."""
        features = self._extract_features(risk_output)
        
        # Calculate reward based on outcome
        reward_map = {
            "SUCCESS": 1.0,           # Correct decision
            "FALSE_POSITIVE": -0.5,   # Blocked legitimate activity
            "FALSE_NEGATIVE": -1.0,   # Allowed malicious activity
            "INCIDENT": -2.0          # Security incident occurred
        }
        reward = reward_map.get(outcome, 0.0)
        
        # For next_features, we use the same features (episodic task)
        next_features = features.copy()
        
        self.rl_manager.train(features, action_taken, reward, next_features)
        logger.info(f"RL model trained: action={action_taken}, outcome={outcome}, reward={reward}")

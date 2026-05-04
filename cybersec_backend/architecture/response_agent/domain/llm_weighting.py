"""LLM-based feature weighting for decision making."""

from __future__ import annotations
import logging
from typing import Dict, Any
from ..infrastructure.llm_client import LLMClient
from .models import RiskAgentOutput, FeatureWeights, DecisionOutput

logger = logging.getLogger(__name__)


class LLMFeatureWeighter:
    """Uses LLM to assign weights to features and calculate action."""
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    def get_feature_weights(self, risk_output: RiskAgentOutput) -> FeatureWeights:
        """Ask LLM to assign weights to different features."""
        prompt = f"""
You are a cybersecurity expert. Analyze this security event and assign weights (0.0 to 1.0) to different features based on their importance for decision making.

Event Details:
- Event ID: {risk_output.event_id}
- User ID: {risk_output.user_id}
- Base Score: {risk_output.base_score}
- Adjusted Risk Score: {risk_output.adjusted_risk_score}
- Risk Level: {risk_output.risk_level}
- Confidence: {risk_output.confidence}

Risk Factors:
{chr(10).join(f"- {rf}" for rf in risk_output.risk_factors)}

Mitigating Factors:
{chr(10).join(f"- {mf}" for mf in risk_output.mitigating_factors)}

Context Summary:
{risk_output.context_summary}

Assign weights to these feature categories:
1. base_score_weight: How much to trust the base anomaly score
2. risk_factors_weight: Importance of identified risk factors
3. mitigating_factors_weight: Importance of mitigating factors
4. context_weight: Importance of contextual information
5. confidence_weight: How much to trust the confidence level

Return ONLY a JSON object with this structure:
{{
    "base_score_weight": 0.0-1.0,
    "risk_factors_weight": 0.0-1.0,
    "mitigating_factors_weight": 0.0-1.0,
    "context_weight": 0.0-1.0,
    "confidence_weight": 0.0-1.0,
    "reasoning": "Brief explanation of weight assignments"
}}
"""
        
        try:
            response = self.llm_client._call_llm(prompt, temperature=0.3)
            weights_data = self.llm_client.extract_json_from_response(response)
            
            return FeatureWeights(
                base_score_weight=weights_data.get("base_score_weight", 0.5),
                risk_factors_weight=weights_data.get("risk_factors_weight", 0.5),
                mitigating_factors_weight=weights_data.get("mitigating_factors_weight", 0.5),
                context_weight=weights_data.get("context_weight", 0.5),
                confidence_weight=weights_data.get("confidence_weight", 0.5),
                reasoning=weights_data.get("reasoning", "")
            )
        except Exception as e:
            logger.error(f"Failed to get feature weights: {e}")
            # Return default weights
            return FeatureWeights(
                base_score_weight=0.5,
                risk_factors_weight=0.5,
                mitigating_factors_weight=0.5,
                context_weight=0.5,
                confidence_weight=0.5,
                reasoning="Using default weights due to LLM error"
            )
    
    def calculate_weighted_decision(
        self, 
        risk_output: RiskAgentOutput, 
        weights: FeatureWeights
    ) -> DecisionOutput:
        """Calculate action based on weighted features."""
        
        # Calculate weighted score
        risk_score = risk_output.adjusted_risk_score * weights.base_score_weight
        
        # Risk factors contribution (count * weight)
        risk_factors_score = (len(risk_output.risk_factors) / 10.0) * weights.risk_factors_weight
        
        # Mitigating factors contribution (negative)
        mitigating_score = -(len(risk_output.mitigating_factors) / 10.0) * weights.mitigating_factors_weight
        
        # Context contribution
        context_score = 0.0
        if risk_output.context_summary:
            # Simple heuristic: more context items = more suspicious
            context_score = (len(risk_output.context_summary) / 10.0) * weights.context_weight
        
        # Confidence adjustment
        confidence_map = {"low": 0.5, "medium": 0.75, "high": 1.0}
        confidence_multiplier = confidence_map.get(risk_output.confidence, 0.75) * weights.confidence_weight
        
        # Final weighted score
        final_score = (risk_score + risk_factors_score + mitigating_score + context_score) * confidence_multiplier
        
        # Determine action based on score
        if final_score >= 0.7:
            action = "BLOCK"
        elif final_score >= 0.5:
            action = "ESCALATE"
        elif final_score >= 0.3:
            action = "MONITOR"
        else:
            action = "ALLOW"
        
        reasoning = f"""
Weighted Decision Analysis:
- Base risk score contribution: {risk_score:.3f}
- Risk factors contribution: {risk_factors_score:.3f}
- Mitigating factors contribution: {mitigating_score:.3f}
- Context contribution: {context_score:.3f}
- Confidence multiplier: {confidence_multiplier:.3f}
- Final weighted score: {final_score:.3f}
- Action: {action}

Weight reasoning: {weights.reasoning}
"""
        
        return DecisionOutput(
            action=action,
            confidence=final_score,
            reasoning=reasoning.strip(),
            source="llm_weighted"
        )
    
    def decide(self, risk_output: RiskAgentOutput) -> DecisionOutput:
        """Main entry point: get weights and calculate decision."""
        weights = self.get_feature_weights(risk_output)
        return self.calculate_weighted_decision(risk_output, weights)

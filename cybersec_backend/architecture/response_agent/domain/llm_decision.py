"""LLM direct decision making."""

from __future__ import annotations
import logging
from ..infrastructure.llm_client import LLMClient
from .models import RiskAgentOutput, DecisionOutput

logger = logging.getLogger(__name__)


class LLMDirectDecision:
    """Uses LLM to make direct decision based on full context."""
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    def decide(self, risk_output: RiskAgentOutput) -> DecisionOutput:
        """Ask LLM to make a direct decision."""
        prompt = f"""
You are a cybersecurity incident response expert. Analyze this security event and recommend an action.

Event Details:
- Event ID: {risk_output.event_id}
- User ID: {risk_output.user_id}
- Timestamp: {risk_output.timestamp}
- Base Score: {risk_output.base_score}
- Adjusted Risk Score: {risk_output.adjusted_risk_score}
- Risk Level: {risk_output.risk_level}
- Current Decision: {risk_output.decision}
- Recommended Action: {risk_output.recommended_action}
- Confidence: {risk_output.confidence}

Risk Factors:
{chr(10).join(f"- {rf}" for rf in risk_output.risk_factors)}

Mitigating Factors:
{chr(10).join(f"- {mf}" for mf in risk_output.mitigating_factors)}

Context Summary:
{risk_output.context_summary}

Based on this information, recommend ONE of these actions:
- ALLOW: Let the activity proceed normally
- MONITOR: Allow but increase monitoring
- ESCALATE: Require human review
- BLOCK: Immediately block the activity

Return ONLY a JSON object with this structure:
{{
    "action": "ALLOW|MONITOR|ESCALATE|BLOCK",
    "confidence": 0.0-1.0,
    "reasoning": "Detailed explanation of why you chose this action"
}}
"""
        
        try:
            response = self.llm_client._call_llm(prompt, temperature=0.5)
            decision_data = self.llm_client.extract_json_from_response(response)
            
            action = decision_data.get("action", "MONITOR")
            confidence = float(decision_data.get("confidence", 0.5))
            reasoning = decision_data.get("reasoning", "")
            
            # Validate action
            valid_actions = ["ALLOW", "MONITOR", "ESCALATE", "BLOCK"]
            if action not in valid_actions:
                logger.warning(f"Invalid action '{action}' from LLM, defaulting to MONITOR")
                action = "MONITOR"
            
            return DecisionOutput(
                action=action,
                confidence=confidence,
                reasoning=reasoning,
                source="llm_direct"
            )
            
        except Exception as e:
            logger.error(f"LLM direct decision failed: {e}")
            # Fallback to risk level mapping
            action_map = {
                "LOW": "ALLOW",
                "MEDIUM": "MONITOR",
                "HIGH": "ESCALATE"
            }
            action = action_map.get(risk_output.risk_level, "MONITOR")
            
            return DecisionOutput(
                action=action,
                confidence=0.5,
                reasoning=f"Fallback decision based on risk level {risk_output.risk_level} due to LLM error",
                source="llm_direct"
            )

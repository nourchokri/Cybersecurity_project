"""LLM orchestrator that combines all decisions."""

from __future__ import annotations
import logging
from ..infrastructure.llm_client import LLMClient
from .models import RiskAgentOutput, DecisionOutput

logger = logging.getLogger(__name__)


class LLMOrchestrator:
    """Orchestrates final decision by comparing all three approaches."""
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    def orchestrate(
        self,
        risk_output: RiskAgentOutput,
        llm_weighted: DecisionOutput,
        llm_direct: DecisionOutput,
        rl_decision: DecisionOutput
    ) -> tuple[str, float, str]:
        """
        Compare all three decisions and make final choice.
        Returns: (final_action, confidence, reasoning)
        """
        prompt = f"""
You are a cybersecurity decision orchestrator. Three different AI systems have analyzed a security event and made recommendations. Your job is to synthesize their inputs and make the FINAL decision.

Original Event:
- Event ID: {risk_output.event_id}
- User ID: {risk_output.user_id}
- Risk Level: {risk_output.risk_level}
- Adjusted Risk Score: {risk_output.adjusted_risk_score}

Decision 1 - LLM Weighted Features:
- Action: {llm_weighted.action}
- Confidence: {llm_weighted.confidence:.3f}
- Reasoning: {llm_weighted.reasoning}

Decision 2 - LLM Direct Analysis:
- Action: {llm_direct.action}
- Confidence: {llm_direct.confidence:.3f}
- Reasoning: {llm_direct.reasoning}

Decision 3 - RL Model (Learned from Past):
- Action: {rl_decision.action}
- Confidence: {rl_decision.confidence:.3f}
- Reasoning: {rl_decision.reasoning}

Analyze these three recommendations and make a FINAL decision. Consider:
1. Agreement level: Do all three agree? If not, why might they differ?
2. Confidence levels: Which system is most confident?
3. Risk level: Does the original risk level support any particular action?
4. Historical learning: The RL model learned from past outcomes - should we trust it?

Return ONLY a JSON object:
{{
    "final_action": "ALLOW|MONITOR|ESCALATE|BLOCK",
    "confidence": 0.0-1.0,
    "reasoning": "Detailed explanation of why you chose this action over the others"
}}
"""
        
        try:
            logger.info("Calling LLM orchestrator...")
            response = self.llm_client._call_llm(prompt, temperature=0.3, max_tokens=1500)
            logger.debug(f"LLM orchestrator raw response: {response[:500]}...")
            
            result = self.llm_client.extract_json_from_response(response)
            logger.info(f"Orchestrator parsed result: {result}")
            
            final_action = result.get("final_action", "MONITOR")
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "")
            
            # Validate action
            valid_actions = ["ALLOW", "MONITOR", "ESCALATE", "BLOCK", "MFA_CHALLENGE"]
            if final_action not in valid_actions:
                logger.warning(f"Invalid final action '{final_action}', defaulting to ESCALATE")
                final_action = "ESCALATE"
            
            logger.info(f"Orchestrator decision: {final_action} (confidence: {confidence})")
            return final_action, confidence, reasoning
            
        except Exception as e:
            logger.error(f"Orchestration failed with exception: {type(e).__name__}: {str(e)}", exc_info=True)
            # Fallback: majority vote
            actions = [llm_weighted.action, llm_direct.action, rl_decision.action]
            final_action = max(set(actions), key=actions.count)
            
            # Average confidence
            avg_confidence = (llm_weighted.confidence + llm_direct.confidence + rl_decision.confidence) / 3
            
            reasoning = f"""
Fallback majority vote due to orchestration error:
- LLM Weighted: {llm_weighted.action}
- LLM Direct: {llm_direct.action}
- RL Model: {rl_decision.action}
- Final (majority): {final_action}
- Average confidence: {avg_confidence:.3f}
"""
            
            return final_action, avg_confidence, reasoning
    
    def explain_risk(self, risk_output: RiskAgentOutput, final_action: str) -> str:
        """Generate explanation of why risk is high/medium/low."""
        prompt = f"""
You are a cybersecurity analyst. Explain to a security operator WHY this event has a {risk_output.risk_level} risk level.

Event Details:
- Event ID: {risk_output.event_id}
- User ID: {risk_output.user_id}
- Risk Level: {risk_output.risk_level}
- Base Score: {risk_output.base_score}
- Adjusted Risk Score: {risk_output.adjusted_risk_score}
- Risk Adjustment: {risk_output.risk_adjustment}

Risk Factors:
{chr(10).join(f"- {rf}" for rf in risk_output.risk_factors)}

Mitigating Factors:
{chr(10).join(f"- {mf}" for mf in risk_output.mitigating_factors)}

Context:
{risk_output.context_summary}

Provide a clear, concise explanation (2-3 sentences) of why this event is considered {risk_output.risk_level} risk.
Focus on the most important factors.
"""
        
        try:
            return self.llm_client._call_llm(prompt, temperature=0.5, max_tokens=500)
        except Exception as e:
            logger.error(f"Risk explanation failed: {e}")
            return f"Risk level {risk_output.risk_level} based on adjusted score {risk_output.adjusted_risk_score:.3f}"
    
    def explain_action(
        self, 
        risk_output: RiskAgentOutput, 
        final_action: str,
        orchestrator_reasoning: str
    ) -> str:
        """Generate explanation of why this specific action was chosen."""
        prompt = f"""
You are a cybersecurity analyst explaining a security decision to an operator.

CRITICAL INSTRUCTION: The final action "{final_action}" and risk level "{risk_output.risk_level}" have ALREADY been determined by the security system. Do NOT question them, suggest they are wrong, or say there's been a mistake. Your ONLY job is to explain WHY this decision was made and what it accomplishes.

Event Details:
- Risk Level: {risk_output.risk_level}
- Adjusted Risk Score: {risk_output.adjusted_risk_score}
- Final Action: {final_action}

Decision Reasoning:
{orchestrator_reasoning}

Provide a clear, authoritative explanation (2-3 sentences) covering:
1. Why the "{final_action}" action is appropriate for this {risk_output.risk_level} risk level
2. What this action will accomplish
3. What happens next

Be confident and direct. Do not second-guess the decision.
"""
        
        try:
            return self.llm_client._call_llm(prompt, temperature=0.5, max_tokens=500)
        except Exception as e:
            logger.error(f"Action explanation failed: {e}")
            action_defaults = {
                "ALLOW": "Activity is allowed to proceed normally with standard logging.",
                "MONITOR": "Activity is allowed but will be monitored more closely for suspicious patterns.",
                "ESCALATE": "Activity requires human review before proceeding.",
                "BLOCK": "Activity is immediately blocked to prevent potential security incident."
            }
            return action_defaults.get(final_action, "Action will be executed as determined by the system.")

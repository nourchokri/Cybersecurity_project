"""Main orchestration service for Response Agent."""

from __future__ import annotations
import logging
from typing import Dict, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..domain.models import (
    RiskAgentOutput, 
    FinalDecision,
    DecisionOutput
)
from ..domain.llm_weighting import LLMFeatureWeighter
from ..domain.llm_decision import LLMDirectDecision
from ..domain.rl_decision import RLDecisionMaker
from ..domain.llm_orchestrator import LLMOrchestrator
from ..skills.action_executor import ActionExecutor

logger = logging.getLogger(__name__)


class ResponseOrchestrationService:
    """Main service that orchestrates the entire response pipeline."""
    
    def __init__(self, use_mock_twilio: bool = False):
        self.llm_weighter = LLMFeatureWeighter()
        self.llm_direct = LLMDirectDecision()
        self.rl_decision_maker = RLDecisionMaker()
        self.orchestrator = LLMOrchestrator()
        self.action_executor = ActionExecutor(use_mock_twilio=use_mock_twilio)
        
        logger.info("Response Orchestration Service initialized")
    
    def process_risk_decision(self, risk_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point: process risk agent output and make final decision.
        
        Pipeline:
        1. Parse risk agent output
        2. Run 3 decision methods in parallel:
           - LLM feature weighting
           - LLM direct decision
           - RL model decision
        3. LLM orchestrator combines all three
        4. Execute action based on risk level
        5. Generate explanations
        """
        try:
            # Step 1: Parse input
            risk_output = RiskAgentOutput.from_dict(risk_data)
            logger.info(f"Processing event {risk_output.event_id} with risk level {risk_output.risk_level}")
            
            # Step 2: Run three decision methods in parallel
            logger.info("Running parallel decision analysis...")
            llm_weighted, llm_direct_dec, rl_dec = self._run_parallel_decisions(risk_output)
            
            # Step 3: Orchestrate final decision
            logger.info("Orchestrating final decision...")
            final_action, confidence, orchestrator_reasoning = self.orchestrator.orchestrate(
                risk_output, llm_weighted, llm_direct_dec, rl_dec
            )
            
            # CRITICAL: Hard override for HIGH risk - always BLOCK
            if risk_output.risk_level == "HIGH":
                logger.warning(f"HIGH RISK OVERRIDE: Forcing action from {final_action} to BLOCK")
                final_action = "BLOCK"
                confidence = max(confidence, 0.9)  # Boost confidence for forced decision
                orchestrator_reasoning = f"[HIGH RISK OVERRIDE] Original decision was {final_action}, but HIGH risk level mandates BLOCK action. " + orchestrator_reasoning
            elif risk_output.risk_level == "MEDIUM":
                # MEDIUM risk floor - never ALLOW or MONITOR, minimum is MFA_CHALLENGE
                if final_action in ["ALLOW", "MONITOR"]:
                    logger.warning(f"MEDIUM RISK FLOOR: Forcing action from {final_action} to MFA_CHALLENGE")
                    original_action = final_action
                    final_action = "MFA_CHALLENGE"
                    orchestrator_reasoning = f"[MEDIUM RISK FLOOR] Original decision was {original_action}, but MEDIUM risk requires at minimum MFA challenge. " + orchestrator_reasoning
            
            # Step 4: Generate explanations
            logger.info("Generating explanations...")
            risk_explanation = self.orchestrator.explain_risk(risk_output, final_action)
            action_explanation = self.orchestrator.explain_action(
                risk_output, final_action, orchestrator_reasoning
            )
            
            # Step 5: Create final decision object
            final_decision = FinalDecision(
                event_id=risk_output.event_id,
                user_id=risk_output.user_id,
                timestamp=risk_output.timestamp or datetime.now().isoformat(),
                risk_level=risk_output.risk_level,
                final_action=final_action,
                execution_status="PENDING",
                llm_weighted_decision=llm_weighted,
                llm_direct_decision=llm_direct_dec,
                rl_decision=rl_dec,
                orchestrator_reasoning=orchestrator_reasoning,
                confidence=confidence,
                risk_explanation=risk_explanation,
                action_explanation=action_explanation
            )
            
            # Step 6: Execute action based on risk level
            logger.info(f"Executing action for risk level: {risk_output.risk_level}")
            execution_status, twilio_call_sid = self.action_executor.execute(
                risk_output, final_decision
            )
            
            final_decision.execution_status = execution_status
            final_decision.twilio_call_sid = twilio_call_sid
            final_decision.user_approval_required = (execution_status == "PENDING_USER")
            
            # Step 7: Train RL model based on execution
            # For HIGH risk auto-executed, assume SUCCESS (we blocked a threat)
            # For LOW risk logged, assume SUCCESS (we correctly allowed safe activity)
            # For MEDIUM risk, we'll train when user responds
            if execution_status == "AUTO_EXECUTED":
                outcome = "SUCCESS"  # We blocked a high-risk threat
                logger.info(f"Training RL model: HIGH risk auto-executed as {final_action}")
                try:
                    self.rl_decision_maker.train_from_feedback(risk_output, final_action, outcome)
                except Exception as e:
                    logger.error(f"RL training failed: {e}")
            elif execution_status == "LOGGED":
                outcome = "SUCCESS"  # We correctly allowed low-risk activity
                logger.info(f"Training RL model: LOW risk logged as {final_action}")
                try:
                    self.rl_decision_maker.train_from_feedback(risk_output, final_action, outcome)
                except Exception as e:
                    logger.error(f"RL training failed: {e}")
            
            logger.info(f"Response processing complete: action={final_action}, status={execution_status}")
            
            return {
                "ok": True,
                "decision": final_decision.to_dict()
            }
            
        except Exception as e:
            logger.exception(f"Response processing failed: {e}")
            return {
                "ok": False,
                "error": str(e)
            }
    
    def _run_parallel_decisions(
        self, 
        risk_output: RiskAgentOutput
    ) -> tuple[DecisionOutput, DecisionOutput, DecisionOutput]:
        """Run three decision methods in parallel."""
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all three tasks
            future_weighted = executor.submit(self.llm_weighter.decide, risk_output)
            future_direct = executor.submit(self.llm_direct.decide, risk_output)
            future_rl = executor.submit(self.rl_decision_maker.decide, risk_output)
            
            # Wait for all to complete
            llm_weighted = future_weighted.result()
            llm_direct_dec = future_direct.result()
            rl_dec = future_rl.result()
        
        return llm_weighted, llm_direct_dec, rl_dec
    
    def handle_user_approval(
        self, 
        event_id: str, 
        user_response: str,
        risk_data: Dict[str, Any],
        action: str
    ) -> Dict[str, Any]:
        """Handle user approval/denial from Twilio callback."""
        try:
            risk_output = RiskAgentOutput.from_dict(risk_data)
            
            approval_status = self.action_executor.handle_user_response(
                event_id, user_response, risk_output, action
            )
            
            # Train RL model based on user feedback
            if approval_status == "APPROVED":
                outcome = "SUCCESS"  # User approved, assume it was correct
            else:
                outcome = "FALSE_POSITIVE"  # User denied, might have been false alarm
            
            self.rl_decision_maker.train_from_feedback(risk_output, action, outcome)
            
            return {
                "ok": True,
                "approval_status": approval_status,
                "event_id": event_id
            }
            
        except Exception as e:
            logger.exception(f"User approval handling failed: {e}")
            return {
                "ok": False,
                "error": str(e)
            }
    
    def train_rl_model(
        self, 
        event_id: str,
        risk_data: Dict[str, Any],
        action_taken: str,
        outcome: str
    ) -> Dict[str, Any]:
        """Train RL model from feedback."""
        try:
            risk_output = RiskAgentOutput.from_dict(risk_data)
            self.rl_decision_maker.train_from_feedback(risk_output, action_taken, outcome)
            
            return {
                "ok": True,
                "message": "RL model trained successfully",
                "event_id": event_id
            }
        except Exception as e:
            logger.exception(f"RL training failed: {e}")
            return {
                "ok": False,
                "error": str(e)
            }
    
    def get_rl_stats(self) -> Dict[str, Any]:
        """Get RL model statistics."""
        return self.rl_decision_maker.rl_manager.get_stats()


# Singleton instance
_service_instance = None


def get_orchestration_service(use_mock_twilio: bool = False) -> ResponseOrchestrationService:
    """Get or create singleton service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ResponseOrchestrationService(use_mock_twilio=use_mock_twilio)
    return _service_instance

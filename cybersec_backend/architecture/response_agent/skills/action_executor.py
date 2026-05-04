"""Execute actions based on risk level and decision."""

from __future__ import annotations
import logging
from typing import Optional
from django.conf import settings
from ..infrastructure.twilio_client import TwilioClient, MockTwilioClient
from ..domain.models import RiskAgentOutput, FinalDecision

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Executes actions based on risk level."""
    
    def __init__(self, use_mock_twilio: bool = False):
        if use_mock_twilio:
            self.twilio_client = MockTwilioClient()
        else:
            self.twilio_client = TwilioClient()
    
    def execute(
        self, 
        risk_output: RiskAgentOutput,
        final_decision: FinalDecision
    ) -> tuple[str, Optional[str]]:
        """
        Execute action based on risk level.
        Returns: (execution_status, twilio_call_sid)
        
        - HIGH risk: Auto-execute
        - MEDIUM risk: Call user for approval
        - LOW risk: Just log
        """
        risk_level = risk_output.risk_level
        action = final_decision.final_action
        
        if risk_level == "HIGH":
            # Auto-execute for high risk
            logger.warning(f"HIGH RISK - Auto-executing action: {action} for event {risk_output.event_id}")
            self._execute_action(action, risk_output)
            return "AUTO_EXECUTED", None
        
        elif risk_level == "MEDIUM":
            # Call user for approval
            logger.info(f"MEDIUM RISK - Requesting user approval for action: {action} for event {risk_output.event_id}")
            call_sid = self._request_user_approval(risk_output, action)
            return "PENDING_USER", call_sid
        
        else:  # LOW risk
            # Just log, no action needed
            logger.info(f"LOW RISK - No action needed for event {risk_output.event_id}, logging only")
            return "LOGGED", None
    
    def _execute_action(self, action: str, risk_output: RiskAgentOutput):
        """Execute the actual security action."""
        # This is where you'd integrate with your security infrastructure
        # For now, we'll just log the action
        
        if action == "BLOCK":
            logger.critical(f"BLOCKING user {risk_output.user_id} - Event: {risk_output.event_id}")
            # TODO: Integrate with firewall/access control system
            # Example: firewall_client.block_user(risk_output.user_id)
        
        elif action == "MFA_CHALLENGE":
            logger.warning(f"MFA CHALLENGE required for user {risk_output.user_id} - Event: {risk_output.event_id}")
            # TODO: Send MFA challenge to user
            # Example: mfa_client.send_challenge(risk_output.user_id)
        
        elif action == "ESCALATE":
            logger.warning(f"ESCALATING event {risk_output.event_id} to security team")
            # TODO: Send to SIEM/ticketing system
            # Example: siem_client.create_incident(risk_output)
        
        elif action == "MONITOR":
            logger.info(f"MONITORING user {risk_output.user_id} - Event: {risk_output.event_id}")
            # TODO: Increase monitoring level
            # Example: monitoring_client.increase_level(risk_output.user_id)
        
        elif action == "ALLOW":
            logger.info(f"ALLOWING activity - Event: {risk_output.event_id}")
            # No action needed, just log
        
        else:
            logger.error(f"Unknown action: {action}")
    
    def _request_user_approval(
        self, 
        risk_output: RiskAgentOutput, 
        action: str
    ) -> Optional[str]:
        """Request user approval via Twilio call."""
        # Get user's phone number (you'd fetch this from your user database)
        user_phone = self._get_user_phone(risk_output.user_id)
        
        if not user_phone:
            logger.warning(f"No phone number for user {risk_output.user_id}, auto-denying")
            return None
        
        # Get callback URL from settings
        callback_url = getattr(settings, 'RESPONSE_AGENT_CALLBACK_URL', 
                              'http://localhost:8000/api/v1/response/twilio/callback')
        
        # Make the call
        call_sid = self.twilio_client.call_user_for_approval(
            to_number=user_phone,
            event_id=risk_output.event_id,
            user_id=risk_output.user_id,
            risk_level=risk_output.risk_level,
            action=action,
            callback_url=callback_url
        )
        
        if call_sid:
            logger.info(f"Twilio call initiated: {call_sid}")
        else:
            logger.error("Failed to initiate Twilio call")
        
        return call_sid
    
    def _get_user_phone(self, user_id: str) -> Optional[str]:
        """Get user's phone number from database."""
        # TODO: Implement actual database lookup
        # For now, return a test number or None
        
        # Example implementation:
        # from django.contrib.auth import get_user_model
        # User = get_user_model()
        # try:
        #     user = User.objects.get(username=user_id)
        #     return user.profile.phone_number
        # except User.DoesNotExist:
        #     return None
        
        # For testing, return a mock number
        test_phone = getattr(settings, 'TEST_PHONE_NUMBER', None)
        if test_phone:
            logger.info(f"Using test phone number for user {user_id}: {test_phone}")
            return test_phone
        
        logger.warning(f"No phone number configured for user {user_id}")
        return None
    
    def handle_user_response(
        self, 
        event_id: str, 
        user_response: str,
        risk_output: RiskAgentOutput,
        action: str
    ) -> str:
        """
        Handle user's approval/denial response.
        Returns: APPROVED | DENIED
        """
        if user_response == "1":  # Approved
            logger.info(f"User APPROVED action {action} for event {event_id}")
            self._execute_action(action, risk_output)
            return "APPROVED"
        
        elif user_response == "2":  # Denied
            logger.info(f"User DENIED action {action} for event {event_id}")
            return "DENIED"
        
        else:
            logger.warning(f"Invalid user response: {user_response}, defaulting to DENIED")
            return "DENIED"

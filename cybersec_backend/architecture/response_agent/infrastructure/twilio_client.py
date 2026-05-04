"""Twilio client for user interaction on MEDIUM risk events."""

from __future__ import annotations
import logging
from typing import Optional, Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class TwilioClient:
    """Client for Twilio voice calls to get user approval."""
    
    def __init__(self):
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        self.auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        self.from_number = getattr(settings, 'TWILIO_FROM_NUMBER', '')
        self.enabled = bool(self.account_sid and self.auth_token and self.from_number)
        
        if self.enabled:
            try:
                from twilio.rest import Client
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("Twilio client initialized successfully")
            except ImportError:
                logger.warning("Twilio library not installed. Install with: pip install twilio")
                self.enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
                self.enabled = False
        else:
            logger.warning("Twilio not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER in settings")
            self.client = None
    
    def call_user_for_approval(
        self, 
        to_number: str, 
        event_id: str,
        user_id: str,
        risk_level: str,
        action: str,
        callback_url: str
    ) -> Optional[str]:
        """
        Make a voice call to user for approval.
        Returns call SID if successful, None otherwise.
        """
        if not self.enabled:
            logger.warning("Twilio not enabled, cannot make call")
            return None
        
        try:
            # Create TwiML for the call
            twiml_url = f"{callback_url}?event_id={event_id}&user_id={user_id}&action={action}"
            
            call = self.client.calls.create(
                to=to_number,
                from_=self.from_number,
                url=twiml_url,
                method='POST',
                status_callback=f"{callback_url}/status",
                status_callback_method='POST',
                status_callback_event=['completed', 'answered', 'no-answer']
            )
            
            logger.info(f"Twilio call initiated: SID={call.sid}, to={to_number}, event={event_id}")
            return call.sid
            
        except Exception as e:
            logger.error(f"Failed to initiate Twilio call: {e}")
            return None
    
    def get_call_status(self, call_sid: str) -> Optional[Dict[str, Any]]:
        """Get status of a call."""
        if not self.enabled:
            return None
        
        try:
            call = self.client.calls(call_sid).fetch()
            return {
                "sid": call.sid,
                "status": call.status,
                "duration": call.duration,
                "direction": call.direction,
                "answered_by": call.answered_by
            }
        except Exception as e:
            logger.error(f"Failed to get call status: {e}")
            return None
    
    def generate_approval_twiml(self, event_id: str, user_id: str, action: str) -> str:
        """Generate TwiML for approval call."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">
        This is a security alert from your cybersecurity system.
        Event ID: {event_id}.
        User: {user_id}.
        Recommended action: {action}.
        Press 1 to approve this action.
        Press 2 to deny this action.
        Press 3 to hear this message again.
    </Say>
    <Gather numDigits="1" action="/api/v1/response/twilio/gather" method="POST" timeout="10">
        <Say voice="alice">Please press 1 to approve, or 2 to deny.</Say>
    </Gather>
    <Say voice="alice">We did not receive your input. The action will be denied by default. Goodbye.</Say>
</Response>
"""
    
    def send_sms_notification(self, to_number: str, message: str) -> Optional[str]:
        """Send SMS notification (alternative to voice call)."""
        if not self.enabled:
            logger.warning("Twilio not enabled, cannot send SMS")
            return None
        
        try:
            sms = self.client.messages.create(
                to=to_number,
                from_=self.from_number,
                body=message
            )
            logger.info(f"SMS sent: SID={sms.sid}, to={to_number}")
            return sms.sid
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return None


class MockTwilioClient(TwilioClient):
    """Mock Twilio client for testing without actual calls."""
    
    def __init__(self):
        self.enabled = True
        self.client = None
        self.mock_calls = []
        logger.info("Mock Twilio client initialized (no real calls will be made)")
    
    def call_user_for_approval(self, to_number: str, event_id: str, user_id: str, 
                              risk_level: str, action: str, callback_url: str) -> str:
        call_sid = f"MOCK_CALL_{len(self.mock_calls)}"
        self.mock_calls.append({
            "sid": call_sid,
            "to": to_number,
            "event_id": event_id,
            "user_id": user_id,
            "action": action,
            "status": "completed"
        })
        logger.info(f"Mock call created: {call_sid}")
        return call_sid
    
    def get_call_status(self, call_sid: str) -> Dict[str, Any]:
        for call in self.mock_calls:
            if call["sid"] == call_sid:
                return call
        return {"sid": call_sid, "status": "not_found"}
    
    def send_sms_notification(self, to_number: str, message: str) -> str:
        sms_sid = f"MOCK_SMS_{len(self.mock_calls)}"
        logger.info(f"Mock SMS sent: {sms_sid}")
        return sms_sid

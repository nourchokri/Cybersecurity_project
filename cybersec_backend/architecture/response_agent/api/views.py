"""API views for Response Agent."""

from __future__ import annotations
import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponse

from .serializers import (
    RiskAgentOutputSerializer,
    FinalDecisionSerializer,
    UserApprovalSerializer,
    RLTrainingSerializer
)
from ..application.orchestration_service import get_orchestration_service

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """GET /api/v1/response/health/"""
    
    def get(self, request):
        return Response({
            "status": "ok",
            "agent": "response_agent",
            "version": "1.0.0"
        })


class ProcessRiskDecisionView(APIView):
    """
    POST /api/v1/response/process/
    
    Main endpoint: receives risk agent output and returns final decision.
    """
    
    def post(self, request):
        serializer = RiskAgentOutputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid risk data", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = get_orchestration_service(use_mock_twilio=True)  # Use mock for testing
            result = service.process_risk_decision(serializer.validated_data)
            
            if result.get("ok"):
                output = FinalDecisionSerializer(result["decision"])
                return Response(output.data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": result.get("error", "Unknown error")},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            logger.exception("Failed to process risk decision")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserApprovalView(APIView):
    """
    POST /api/v1/response/approval/
    
    Handle user approval/denial (called after Twilio interaction).
    """
    
    def post(self, request):
        serializer = UserApprovalSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid approval data", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = get_orchestration_service()
            result = service.handle_user_approval(
                event_id=serializer.validated_data["event_id"],
                user_response=serializer.validated_data["user_response"],
                risk_data=serializer.validated_data["risk_data"],
                action=serializer.validated_data["action"]
            )
            
            if result.get("ok"):
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": result.get("error")},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            logger.exception("Failed to handle user approval")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RLTrainingView(APIView):
    """
    POST /api/v1/response/train/
    
    Train RL model from feedback.
    """
    
    def post(self, request):
        serializer = RLTrainingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid training data", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = get_orchestration_service()
            result = service.train_rl_model(
                event_id=serializer.validated_data["event_id"],
                risk_data=serializer.validated_data["risk_data"],
                action_taken=serializer.validated_data["action_taken"],
                outcome=serializer.validated_data["outcome"]
            )
            
            if result.get("ok"):
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": result.get("error")},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            logger.exception("Failed to train RL model")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RLStatsView(APIView):
    """GET /api/v1/response/rl/stats/"""
    
    def get(self, request):
        try:
            service = get_orchestration_service()
            stats = service.get_rl_stats()
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Failed to get RL stats")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TwilioCallbackView(APIView):
    """
    POST /api/v1/response/twilio/callback/
    
    Twilio callback for voice call TwiML.
    """
    
    def post(self, request):
        event_id = request.GET.get('event_id', '')
        user_id = request.GET.get('user_id', '')
        action = request.GET.get('action', '')
        
        service = get_orchestration_service()
        twiml = service.action_executor.twilio_client.generate_approval_twiml(
            event_id, user_id, action
        )
        
        return HttpResponse(twiml, content_type='text/xml')


class TwilioGatherView(APIView):
    """
    POST /api/v1/response/twilio/gather/
    
    Handle user's digit input from Twilio.
    """
    
    def post(self, request):
        digits = request.POST.get('Digits', '')
        event_id = request.GET.get('event_id', '')
        
        if digits == "1":
            twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Thank you. The action has been approved. Goodbye.</Say>
</Response>
"""
        elif digits == "2":
            twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Thank you. The action has been denied. Goodbye.</Say>
</Response>
"""
        elif digits == "3":
            # Redirect back to main callback to repeat message
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Redirect>/api/v1/response/twilio/callback/?event_id={event_id}</Redirect>
</Response>
"""
        else:
            twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Invalid input. The action has been denied. Goodbye.</Say>
</Response>
"""
        
        return HttpResponse(twiml, content_type='text/xml')


class TwilioStatusView(APIView):
    """
    POST /api/v1/response/twilio/status/
    
    Handle Twilio call status callbacks.
    """
    
    def post(self, request):
        call_sid = request.POST.get('CallSid', '')
        call_status = request.POST.get('CallStatus', '')
        
        logger.info(f"Twilio call status: SID={call_sid}, Status={call_status}")
        
        # You could store this in database for tracking
        
        return HttpResponse(status=200)

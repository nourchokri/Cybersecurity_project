"""DRF Views for the Attacker Agent API."""
import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    InjectAttackSerializer,
    StartAgentSerializer,
    ListPatternsSerializer
)
from ..application.attacker_service import get_attacker_service

logger = logging.getLogger('attacker_agent')


class HealthCheckView(APIView):
    """GET /api/v1/attacker/health/"""
    
    def get(self, request):
        try:
            service = get_attacker_service()
            return Response({
                'status': 'healthy',
                'agent': 'attacker_agent',
                'version': '1.0.0',
                'capabilities': [
                    'intelligent_attack_generation',
                    'context_aware_simulation',
                    'llm_powered_decisions',
                    'cert_r42_patterns'
                ]
            })
        except Exception as e:
            return Response(
                {'status': 'error', 'error': str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


class ListPatternsView(APIView):
    """GET /api/v1/attacker/patterns/
    
    List available attack patterns with optional filtering.
    """
    
    def get(self, request):
        serializer = ListPatternsSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid parameters', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = get_attacker_service()
            result = service.list_attack_patterns(
                category=serializer.validated_data.get('category'),
                severity=serializer.validated_data.get('severity')
            )
            
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception('Failed to list attack patterns')
            return Response(
                {'error': f'Failed to list patterns: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class InjectAttackView(APIView):
    """POST /api/v1/attacker/inject/
    
    Inject a single attack pattern.
    """
    
    def post(self, request):
        serializer = InjectAttackSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid request', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = get_attacker_service()
            result = service.inject_attack(
                attack_id=serializer.validated_data['attack_id'],
                user_id=serializer.validated_data.get('user_id'),
                device_id=serializer.validated_data.get('device_id')
            )
            
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception('Attack injection failed')
            return Response(
                {'error': f'Injection failed: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StartAgentView(APIView):
    """POST /api/v1/attacker/start/
    
    Start the continuous adversarial agent.
    """
    
    def post(self, request):
        serializer = StartAgentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid request', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = get_attacker_service()
            result = service.start_agent(
                interval_seconds=serializer.validated_data['interval_seconds'],
                max_attacks=serializer.validated_data.get('max_attacks')
            )
            
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception('Failed to start agent')
            return Response(
                {'error': f'Failed to start agent: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StopAgentView(APIView):
    """POST /api/v1/attacker/stop/
    
    Stop the continuous adversarial agent.
    """
    
    def post(self, request):
        try:
            service = get_attacker_service()
            result = service.stop_agent()
            
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception('Failed to stop agent')
            return Response(
                {'error': f'Failed to stop agent: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SimulateAttackView(APIView):
    """POST /api/v1/attacker/simulate/
    
    Run exactly ONE complete 5-phase attack cycle.
    Unlike start/, this does not loop continuously.
    """
    
    def post(self, request):
        try:
            service = get_attacker_service()
            result = service.simulate_attack()
            
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception('Failed to simulate attack')
            return Response(
                {'error': f'Failed to simulate attack: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StatsView(APIView):
    """GET /api/v1/attacker/stats/
    
    Get attack statistics.
    """
    
    def get(self, request):
        try:
            service = get_attacker_service()
            result = service.get_stats()
            
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception('Failed to get stats')
            return Response(
                {'error': f'Failed to get stats: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class HistoryView(APIView):
    """GET /api/v1/attacker/history/
    
    Get attack history.
    """
    
    def get(self, request):
        limit = request.query_params.get('limit', 100)
        
        try:
            service = get_attacker_service()
            result = service.get_history(limit=int(limit))
            
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception('Failed to get history')
            return Response(
                {'error': f'Failed to get history: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogsView(APIView):
    """GET /api/v1/attacker/logs/
    
    Get recent agent logs for frontend display.
    """
    
    def get(self, request):
        from ..application.log_manager import get_recent_logs
        
        limit = request.query_params.get('limit', 50)
        
        try:
            logs = get_recent_logs(limit=int(limit))
            
            return Response({
                'ok': True,
                'logs': logs,
                'count': len(logs)
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception('Failed to get logs')
            return Response(
                {'error': f'Failed to get logs: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BehaviorResultView(APIView):
    """GET /api/v1/attacker/behavior-result/
    
    Get the latest A2A behavior analysis result from the last attack simulation.
    The attacker agent forwards injected events to the Behavior Agent via A2A
    after each simulation. This endpoint returns that result.
    """
    
    def get(self, request):
        try:
            service = get_attacker_service()
            result = service.get_behavior_result()
            
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception('Failed to get behavior result')
            return Response(
                {'error': f'Failed to get behavior result: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

"""DRF Views for the Data Agent API."""
import logging
import json
import time
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import StreamingHttpResponse

from .serializers import (
    CollectRequestSerializer,
    QueryRequestSerializer,
    AnalyzeRequestSerializer,
    InjectAttackSerializer
)
from ..application.data_service import get_data_service

logger = logging.getLogger('data_agent')


class HealthCheckView(APIView):
    """GET /api/v1/data/health/"""
    
    def get(self, request):
        try:
            service = get_data_service()
            return Response({
                'status': 'healthy',
                'agent': 'data_agent',
                'version': '1.0.0',
                'monitor': 'B',
                'capabilities': [
                    'event_collection',
                    'event_storage',
                    'llm_analysis',
                    'attack_injection'
                ]
            })
        except Exception as e:
            return Response(
                {'status': 'error', 'error': str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


class CollectEventsView(APIView):
    """POST /api/v1/data/collect/
    
    Trigger event collection from specified collectors.
    """
    
    def post(self, request):
        serializer = CollectRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid request', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = get_data_service()
            collectors = serializer.validated_data.get('collectors', [])
            result = service.collect_events(collectors)
            
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception('Event collection failed')
            return Response(
                {'error': f'Collection failed: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CollectEventsStreamView(APIView):
    """POST /api/v1/data/collect-stream/
    
    Streaming version of event collection with real-time progress updates.
    Returns Server-Sent Events (SSE) stream.
    """
    
    def post(self, request):
        serializer = CollectRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid request', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        collectors = serializer.validated_data.get('collectors', [])
        
        def event_stream():
            """Generator that yields SSE-formatted progress updates."""
            try:
                service = get_data_service()
                
                # Use the streaming generator from data_service
                for update in service.collect_events_streaming(collectors):
                    if update['type'] == 'log':
                        # Progress log message
                        yield f"data: {json.dumps({'type': update['level'], 'message': update['message']})}\n\n"
                    elif update['type'] == 'complete':
                        # Final result
                        yield f"data: {json.dumps({'type': 'complete', 'result': update['result']})}\n\n"
                
            except Exception as e:
                logger.exception('Streaming collection failed')
                yield f"data: {json.dumps({'type': 'error', 'message': f'❌ Collection failed: {str(e)}'})}\n\n"
        
        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response


# ============================================================================
# CRITICAL: This is the pipeline endpoint that forwards to Behavior Agent
# ============================================================================
class PipelineCollectView(APIView):
    """POST /api/v1/data/pipeline-collect/
    
    Pipeline mode: Collect events and forward to Behavior Agent via A2A.
    This endpoint is called when "Start Pipeline" button is clicked.
    
    Flow:
    1. Collect events from MCP collectors
    2. Extract events from collection results
    3. Aggregate events into sessions
    4. Send sessions to Behavior Agent via HTTP
    5. Return combined results
    """
    
    def post(self, request):
        serializer = CollectRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid request', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = get_data_service()
            collectors = serializer.validated_data.get('collectors', [])
            
            # THIS IS THE KEY METHOD - it orchestrates the entire pipeline
            result = service.collect_and_forward_to_behavior(collectors)
            
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception('Pipeline collection failed')
            return Response(
                {'error': f'Pipeline failed: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QueryEventsView(APIView):
    """POST /api/v1/data/query/
    
    Query stored events with filters.
    """
    
    def post(self, request):
        serializer = QueryRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid query', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = get_data_service()
            result = service.query_events(serializer.validated_data)
            
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception('Event query failed')
            return Response(
                {'error': f'Query failed: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AnalyzeEventsView(APIView):
    """POST /api/v1/data/analyze/
    
    Analyze events using LLM agent with natural language query.
    """
    
    def post(self, request):
        serializer = AnalyzeRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid analysis request', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = get_data_service()
            result = service.analyze_events(serializer.validated_data)
            
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception('Event analysis failed')
            return Response(
                {'error': f'Analysis failed: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class InjectAttackView(APIView):
    """POST /api/v1/data/inject-attack/
    
    Inject synthetic attack patterns for testing.
    """
    
    def post(self, request):
        serializer = InjectAttackSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid injection request', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = get_data_service()
            result = service.inject_attack(serializer.validated_data)
            
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception('Attack injection failed')
            return Response(
                {'error': f'Injection failed: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StatsView(APIView):
    """GET /api/v1/data/stats/
    
    Get statistics about collected events.
    """
    
    def get(self, request):
        try:
            service = get_data_service()
            result = service.get_stats()
            
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception('Stats retrieval failed')
            return Response(
                {'error': f'Stats failed: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

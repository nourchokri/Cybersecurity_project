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


class PipelineCollectView(APIView):
    """POST /api/v1/data/pipeline-collect/
    
    Pipeline mode: Collect events and forward to Behavior Agent via A2A.
    This endpoint is called when "Start Pipeline" button is clicked.
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


class StoredEventsView(APIView):
    """GET /api/v1/data/stored-events/
    
    Read stored event files from logs/ directory and analyze for network risks.
    Returns events grouped by date with network analysis.
    """
    
    def get(self, request):
        try:
            from pathlib import Path
            import json
            from datetime import datetime
            
            # Get logs directory - MCP servers create logs in data_agent root
            logs_dir = Path(__file__).parent.parent / 'logs'
            
            if not logs_dir.exists():
                return Response({
                    'ok': False,
                    'error': 'No stored events found',
                    'message': 'logs/ directory does not exist. Run data collection first.',
                    'logs_path': str(logs_dir.absolute()),
                    'files': []
                }, status=status.HTTP_200_OK)
            
            # Find all event files
            event_files = sorted(logs_dir.glob('events_*.jsonl'), reverse=True)
            
            if not event_files:
                return Response({
                    'ok': False,
                    'error': 'No event files found',
                    'message': 'No events_*.jsonl files in logs/ directory',
                    'files': []
                }, status=status.HTTP_200_OK)
            
            # Read events from all files
            events_by_date = {}
            total_events = 0
            network_events_count = 0
            
            for file_path in event_files:
                date_str = file_path.stem.replace('events_', '')  # Extract date from filename
                events = []
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                event = json.loads(line)
                                events.append(event)
                                total_events += 1
                                
                                # Count network events
                                if event.get('event_category') == 'network' or event.get('event_type') == 'network_connection':
                                    network_events_count += 1
                                    
                            except json.JSONDecodeError as e:
                                logger.warning(f"Corrupted event in {file_path} line {line_num}: {e}")
                                continue
                    
                    if events:
                        events_by_date[date_str] = {
                            'date': date_str,
                            'file': str(file_path.name),
                            'event_count': len(events),
                            'events': events,
                            'network_events': [e for e in events if e.get('event_category') == 'network' or e.get('event_type') == 'network_connection']
                        }
                        
                except Exception as e:
                    logger.error(f"Failed to read {file_path}: {e}")
                    continue
            
            return Response({
                'ok': True,
                'total_events': total_events,
                'network_events_count': network_events_count,
                'files_count': len(events_by_date),
                'events_by_date': events_by_date,
                'message': f'Loaded {total_events} events from {len(events_by_date)} files'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception('Failed to read stored events')
            return Response(
                {'ok': False, 'error': f'Failed to read stored events: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AnalyzeStoredNetworkEventsView(APIView):
    """POST /api/v1/data/analyze-stored-network/
    
    Analyze stored network events from logs/ directory for network risks.
    Sends network events to Network Agent for analysis.
    """
    
    def post(self, request):
        try:
            from pathlib import Path
            import json
            from ..integrations.network_agent_client import NetworkAgentClient
            from ..application.session_aggregator import SessionAggregator
            
            # Optional: filter by date
            date_filter = request.data.get('date')  # e.g., "2026-05-04"
            
            # Get logs directory - MCP servers create logs in data_agent root
            logs_dir = Path(__file__).parent.parent / 'logs'
            
            if not logs_dir.exists():
                return Response({
                    'ok': False,
                    'error': 'No stored events found',
                    'message': 'logs/ directory does not exist',
                    'logs_path': str(logs_dir.absolute())
                }, status=status.HTTP_200_OK)
            
            # Find event files
            if date_filter:
                event_files = [logs_dir / f'events_{date_filter}.jsonl']
            else:
                event_files = sorted(logs_dir.glob('events_*.jsonl'), reverse=True)
            
            # Collect all events
            all_events = []
            for file_path in event_files:
                if not file_path.exists():
                    continue
                    
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                event = json.loads(line)
                                all_events.append(event)
                            except json.JSONDecodeError:
                                continue
                except Exception as e:
                    logger.error(f"Failed to read {file_path}: {e}")
                    continue
            
            if not all_events:
                return Response({
                    'ok': False,
                    'error': 'No events found',
                    'message': 'No events in stored files'
                }, status=status.HTTP_200_OK)
            
            # Aggregate events into sessions
            aggregator = SessionAggregator()
            sessions = aggregator.aggregate_events_to_sessions(all_events)
            
            if not sessions:
                return Response({
                    'ok': False,
                    'error': 'No sessions created',
                    'message': 'Could not aggregate events into sessions'
                }, status=status.HTTP_200_OK)
            
            # Send to Network Agent for analysis
            network_client = NetworkAgentClient()
            network_result = network_client.send_network_sessions(sessions)
            
            return Response({
                'ok': True,
                'total_events': len(all_events),
                'sessions_created': len(sessions),
                'network_result': network_result,
                'message': f'Analyzed {len(all_events)} events from stored files'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception('Failed to analyze stored network events')
            return Response(
                {'ok': False, 'error': f'Analysis failed: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

"""DRF Views for the Behavior Analysis Agent API."""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import SessionInputSerializer, BatchSessionSerializer, AnomalyResultSerializer
from ..application.orchestration_service import get_orchestration_service

logger = logging.getLogger('behavior_agent')


class HealthCheckView(APIView):
    """GET /api/v1/behavior/health/"""

    def get(self, request):
        try:
            service = get_orchestration_service()
            return Response({**service.health(), 'agent': 'behavior_agent', 'version': '1.0.0'})
        except Exception as e:
            return Response(
                {'status': 'error', 'error': str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class ScoreSessionView(APIView):
    """POST /api/v1/behavior/score/

    Score a single user session and return an AnomalyResult.
    Automatically forwards the result to Team 3 (Risk Decision Agent) if flagged.
    """

    def post(self, request):
        serializer = SessionInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid session data', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            service = get_orchestration_service()
        except Exception as e:
            logger.exception('Failed to initialize orchestration service')
            return Response(
                {'error': f'Service initialization failed: {e}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        thread_id = request.data.get('thread_id', f"api_{serializer.validated_data['user_id']}")
        result = service.score_session(serializer.validated_data, thread_id=thread_id)

        if not result.get('ok'):
            return Response(
                {'error': result.get('error', 'Scoring failed')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        ar = result['anomaly_result']

        # Forward to Team 3 with priority based on detection source
        llm_detected_threat = _check_llm_threat_detection(ar)
        should_forward = ar.get('flagged') or llm_detected_threat
        
        if should_forward:
            # Set priority: IF model = HIGH, LLM only = MEDIUM
            priority = 'HIGH' if ar.get('flagged') else 'MEDIUM'
            _forward_to_risk_agent(ar, priority=priority)

        return Response(ar, status=status.HTTP_200_OK)


class BatchScoreView(APIView):
    """POST /api/v1/behavior/batch/

    Score multiple sessions. Returns list of AnomalyResults.
    """

    def post(self, request):
        serializer = BatchSessionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid batch request', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            service = get_orchestration_service()
        except Exception as e:
            return Response(
                {'error': f'Service initialization failed: {e}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        sessions = serializer.validated_data['sessions']
        results  = service.score_batch(sessions)

        output = []
        for r in results:
            if r.get('ok'):
                ar = r['anomaly_result']
                
                # Forward to Team 3 with priority based on detection source
                llm_detected_threat = _check_llm_threat_detection(ar)
                should_forward = ar.get('flagged') or llm_detected_threat
                
                if should_forward:
                    # Set priority: IF model = HIGH, LLM only = MEDIUM
                    priority = 'HIGH' if ar.get('flagged') else 'MEDIUM'
                    _forward_to_risk_agent(ar, priority=priority)
                    
                output.append({'ok': True, 'anomaly_result': ar})
            else:
                output.append({'ok': False, 'error': r.get('error')})

        return Response({'results': output}, status=status.HTTP_200_OK)


class UserBaselineView(APIView):
    """GET /api/v1/behavior/baseline/<user_id>/

    Return the behavioral baseline for a user.
    """

    def get(self, request, user_id: str):
        try:
            service = get_orchestration_service()
            baseline = service.get_baseline(user_id)
            if 'error' in baseline:
                return Response(baseline, status=status.HTTP_404_NOT_FOUND)
            return Response(baseline, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserHistoryView(APIView):
    """GET /api/v1/behavior/history/<user_id>/

    Return recent session scores for a user.
    """

    def get(self, request, user_id: str):
        try:
            service = get_orchestration_service()
            limit   = int(request.query_params.get('limit', 10))
            history = service.get_user_history(user_id, limit=limit)
            return Response({'user_id': user_id, 'history': history}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SampleSessionsView(APIView):
    """GET /api/v1/behavior/sample-sessions/

    Return a curated sample of real sessions from test_sessions.parquet.
    Query params:
      - n      : total sessions to return (default 30)
      - flagged: if "1", return only sessions with at least one anomalous signal
    """

    def get(self, request):
        try:
            import pandas as pd
            from django.conf import settings

            path = getattr(settings, 'TEST_SESSIONS_PATH', None)
            if path is None or not path.exists():
                return Response(
                    {'error': 'test_sessions.parquet not found — check MONITOR_A_PATH'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            df = pd.read_parquet(str(path))

            n       = int(request.query_params.get('n', 30))
            flagged = request.query_params.get('flagged', '0') == '1'

            # Build a representative sample: mix of normal + anomalous sessions
            if flagged:
                mask = (
                    (df['usb_connected'] == 1) |
                    (df['visited_exfil_domain'] == 1) |
                    (df['has_ext_email'] == 1) |
                    (df['is_outside_hours'] == 1) |
                    (df['visited_jobsearch_domain'] == 1)
                )
                sample = df[mask].sample(min(n, mask.sum()), random_state=42)
            else:
                # Stratified: ~40% normal, ~60% with at least one signal
                mask = (
                    (df['usb_connected'] == 1) |
                    (df['visited_exfil_domain'] == 1) |
                    (df['has_ext_email'] == 1) |
                    (df['is_outside_hours'] == 1) |
                    (df['visited_jobsearch_domain'] == 1)
                )
                n_anomalous = int(n * 0.6)
                n_normal    = n - n_anomalous
                anomalous = df[mask].sample(min(n_anomalous, mask.sum()), random_state=42)
                normal    = df[~mask].sample(min(n_normal, (~mask).sum()), random_state=42)
                sample    = pd.concat([anomalous, normal]).sample(frac=1, random_state=42)

            # Serialise to list of dicts — convert numpy types to Python natives
            sessions = []
            for _, row in sample.iterrows():
                sessions.append({
                    'user_id':                  str(row['user_id']),
                    'pc':                       str(row.get('pc', '')),
                    'session_start':            str(row['session_start']),
                    'hour_of_day':              int(row['hour_of_day']),
                    'is_weekend':               int(row['is_weekend']),
                    'is_outside_hours':         int(row['is_outside_hours']),
                    'duration_minutes':         float(row['duration_minutes']),
                    'file_count':               int(row['file_count']),
                    'max_sensitivity':          int(row['max_sensitivity']),
                    'usb_connected':            int(row['usb_connected']),
                    'usb_first_time':           int(row['usb_first_time']),
                    'email_count':              int(row['email_count']),
                    'has_ext_email':            int(row['has_ext_email']),
                    'visited_exfil_domain':     int(row['visited_exfil_domain']),
                    'visited_jobsearch_domain': int(row['visited_jobsearch_domain']),
                    'simulated':                False,
                })

            return Response({'sessions': sessions, 'total': len(sessions)})

        except Exception as e:
            logger.exception('SampleSessionsView error')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ── Internal: forward to Team 3 ───────────────────────────────────────────────

def _check_llm_threat_detection(anomaly_result: dict) -> bool:
    """
    Check if the LLM detected a threat in its analysis, even if the ML model didn't flag it.
    Returns True if LLM analysis contains threat-related keywords.
    """
    analysis = anomaly_result.get('detection_agent_analysis', {})
    analyst_note = analysis.get('analyst_note', '').lower()
    
    # Keywords that indicate LLM detected a threat
    threat_keywords = [
        'threat', 'suspicious', 'malicious', 'attack', 'breach', 'compromise',
        'exfiltration', 'infiltration', 'unauthorized', 'anomalous behavior',
        'security risk', 'potential threat', 'concerning', 'unusual activity'
    ]
    
    return any(keyword in analyst_note for keyword in threat_keywords)


def _forward_to_risk_agent(anomaly_result: dict, priority: str = 'HIGH'):
    """
    POST the AnomalyResult to Team 3's Risk Decision Agent.
    Non-blocking — failure is logged but does not affect the response.
    
    Args:
        anomaly_result: The behavior analysis result
        priority: 'HIGH' for IF model detection, 'MEDIUM' for LLM-only detection
    """
    try:
        import httpx
        from django.conf import settings

        team3_url = getattr(
            settings, 'RISK_AGENT_URL',
            'http://127.0.0.1:8000/api/v1/risk-decision/analyze/'
        )

        # Map our AnomalyResult to Team 3's AnomalyEventSerializer schema
        payload = {
            'event_id':          anomaly_result.get('event_id', ''),
            'user_id':           anomaly_result.get('user_id', ''),
            'timestamp':         anomaly_result.get('timestamp', ''),
            'score':             anomaly_result.get('combined_score', 0.0),
            'combined_score':    anomaly_result.get('combined_score', 0.0),
            'if_score':          anomaly_result.get('if_score'),
            'dimension_scores':  anomaly_result.get('dimension_scores'),
            'triggered_rules':   anomaly_result.get('triggered_rules', []),
            'confidence':        anomaly_result.get('confidence', 'medium'),
            'cold_start':        anomaly_result.get('cold_start', False),
            'simulated':         anomaly_result.get('simulated', False),
            'monitor':           'A',
            'threat_classification': f'{priority}_PRIORITY',  # Add priority classification
        }

        with httpx.Client(timeout=90.0) as client:  # Team 3 LLM call can take 30-60s
            resp = client.post(team3_url, json=payload)
            if resp.status_code == 200:
                detection_source = 'IF_MODEL' if anomaly_result.get('flagged') else 'LLM_ANALYSIS'
                logger.info(
                    f'Forwarded {anomaly_result.get("user_id")} to Team 3 '
                    f'(source={detection_source}, priority={priority}, '
                    f'score={anomaly_result.get("combined_score", 0):.4f})'
                )
            else:
                logger.warning(f'Team 3 returned {resp.status_code}: {resp.text[:200]}')

    except Exception as e:
        logger.warning(f'Failed to forward to Team 3: {e}')

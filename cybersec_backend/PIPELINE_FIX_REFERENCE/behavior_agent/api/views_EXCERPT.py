"""
Behavior Agent API Views - EXCERPT

This shows how the Behavior Agent receives sessions from Data Agent.
This is the RECEIVING side of the pipeline.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import BatchSessionSerializer
from ..application.orchestration_service import get_orchestration_service

import logging
logger = logging.getLogger('behavior_agent')


class BatchScoreView(APIView):
    """POST /api/v1/behavior/batch/
    
    This endpoint receives sessions from Data Agent and scores them.
    """

    def post(self, request):
        # Validate incoming sessions
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

        # Get sessions from request
        sessions = serializer.validated_data['sessions']
        
        # Score each session
        results = service.score_batch(sessions)

        # Format output
        output = []
        for r in results:
            if r.get('ok'):
                ar = r['anomaly_result']
                output.append({'ok': True, 'anomaly_result': ar})
            else:
                output.append({'ok': False, 'error': r.get('error')})

        return Response({'results': output}, status=status.HTTP_200_OK)


# Expected request format:
"""
POST /api/v1/behavior/batch/
{
    "sessions": [
        {
            "user_id": "AAA0001",
            "pc": "PC01",
            "session_start": "2026-05-02T10:00:00",
            "hour_of_day": 10,
            "is_weekend": 0,
            "is_outside_hours": 0,
            "duration_minutes": 30.5,
            "file_count": 5,
            "max_sensitivity": 2,
            "usb_connected": 0,
            "usb_first_time": 0,
            "email_count": 3,
            "has_ext_email": 0,
            "visited_exfil_domain": 0,
            "visited_jobsearch_domain": 0,
            "simulated": false
        },
        ...
    ]
}
"""

# Expected response format:
"""
{
    "results": [
        {
            "ok": true,
            "anomaly_result": {
                "user_id": "AAA0001",
                "flagged": true,
                "combined_score": 0.85,
                "if_score": 0.82,
                "dimension_scores": {...},
                "triggered_rules": ["usb_connected"],
                ...
            }
        },
        ...
    ]
}
"""

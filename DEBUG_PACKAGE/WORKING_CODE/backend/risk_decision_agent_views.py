"""DRF Views for the Risk Decision Agent API."""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    AnomalyEventSerializer,
    BatchRequestSerializer,
    CacheStatsSerializer,
    DecisionOutputSerializer,
)
from ..application.orchestration_service import get_orchestration_service

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """GET /api/v1/risk-decision/health/"""

    def get(self, request):
        return Response({
            "status": "ok",
            "agent": "risk_decision_agent",
            "version": "1.0.0",
        })


class AnalyzeEventView(APIView):
    """POST /api/v1/risk-decision/analyze/

    Receive a single anomaly event from Team 2 (or frontend) and return
    the contextual risk decision.
    """

    def post(self, request):
        serializer = AnomalyEventSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid event data", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            service = get_orchestration_service()
        except Exception as e:
            logger.exception("Failed to initialize orchestration service")
            return Response(
                {"error": f"Service initialization failed: {e}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        result = service.analyze_event(serializer.validated_data)

        if result.get("ok"):
            output = DecisionOutputSerializer(result["decision"])
            return Response(output.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": result.get("error", "Unknown error")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BatchAnalyzeView(APIView):
    """POST /api/v1/risk-decision/batch/

    Analyze multiple events, optionally in parallel.
    """

    def post(self, request):
        serializer = BatchRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid batch request", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        events = serializer.validated_data["events"]
        parallel = serializer.validated_data.get("parallel", 1)

        try:
            service = get_orchestration_service()
        except Exception as e:
            return Response(
                {"error": f"Service initialization failed: {e}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        results = service.analyze_batch(events, parallel=parallel)

        output = []
        for r in results:
            if r.get("ok"):
                output.append({"ok": True, "decision": r["decision"]})
            else:
                output.append({"ok": False, "error": r.get("error")})

        return Response({"results": output}, status=status.HTTP_200_OK)


class CacheStatsView(APIView):
    """GET /api/v1/risk-decision/cache/stats/"""

    def get(self, request):
        try:
            service = get_orchestration_service()
            stats = service.get_cache_stats()
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CacheClearView(APIView):
    """POST /api/v1/risk-decision/cache/clear/"""

    def post(self, request):
        try:
            service = get_orchestration_service()
            service.clear_cache()
            return Response({"status": "cache cleared"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CacheCleanupView(APIView):
    """POST /api/v1/risk-decision/cache/cleanup/"""

    def post(self, request):
        try:
            service = get_orchestration_service()
            removed = service.cleanup_cache()
            return Response(
                {"status": "cleanup complete", "removed": removed},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SampleEventsView(APIView):
    """GET /api/v1/risk-decision/sample-events/

    Returns sample anomaly events (useful for frontend testing).
    """

    def get(self, request):
        try:
            service = get_orchestration_service()
            events = service.get_sample_events()
            return Response({"events": events}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

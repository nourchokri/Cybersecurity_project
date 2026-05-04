"""Root URL configuration for cybersec_backend."""

from django.contrib import admin
from django.urls import include, path
from rest_framework.response import Response
from rest_framework.views import APIView


class APIRootView(APIView):
    """Root endpoint — shows available API routes."""

    def get(self, request):
        return Response({
            "project": "Cybersecurity Multi-Agent SOC Platform",
            "version": "1.0.0",
            "agents": {
                "risk_decision_agent": {
                    "base_url": "/api/v1/risk-decision/",
                    "endpoints": {
                        "health": "GET /api/v1/risk-decision/health/",
                        "analyze": "POST /api/v1/risk-decision/analyze/",
                        "batch": "POST /api/v1/risk-decision/batch/",
                        "sample_events": "GET /api/v1/risk-decision/sample-events/",
                        "cache_stats": "GET /api/v1/risk-decision/cache/stats/",
                        "cache_clear": "POST /api/v1/risk-decision/cache/clear/",
                        "cache_cleanup": "POST /api/v1/risk-decision/cache/cleanup/",
                    },
                },
                "data_agent": {
			"data_agent": {
    			"base_url": "/api/v1/data/",
    			"endpoints": {
        		"health": "GET /api/v1/data/health/",
       		 	"collect": "POST /api/v1/data/collect/",
        		"query": "POST /api/v1/data/query/",
        		"analyze": "POST /api/v1/data/analyze/",
        		"inject_attack": "POST /api/v1/data/inject-attack/",
        		"stats": "GET /api/v1/data/stats/",
    					}
				}

		},
                "behavior_agent": {
                    "base_url": "/api/v1/behavior/",
                    "endpoints": {
                        "health":   "GET /api/v1/behavior/health/",
                        "score":    "POST /api/v1/behavior/score/",
                        "batch":    "POST /api/v1/behavior/batch/",
                        "baseline": "GET /api/v1/behavior/baseline/<user_id>/",
                        "history":  "GET /api/v1/behavior/history/<user_id>/",
                    },
                },
                "response_agent": {"status": "pending"},
            },
        })


urlpatterns = [
    path("", APIRootView.as_view(), name="api-root"),
    path("admin/", admin.site.urls),

    # ── Agent APIs ────────────────────────────────────────────────────────
    path(
        "api/v1/risk-decision/",
        include("architecture.risk_decision_agent.api.urls"),
    ),
    path(
        "api/v1/behavior/",
        include("architecture.behavior_agent.api.urls"),
    ),
    path("api/v1/data/", include("architecture.data_agent.api.urls")),

]

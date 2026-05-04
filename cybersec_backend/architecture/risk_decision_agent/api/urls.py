"""URL routing for the Risk Decision Agent API."""

from django.urls import path

from . import views

app_name = "risk_decision_agent"

urlpatterns = [
    # Core endpoints
    path("analyze/", views.AnalyzeEventView.as_view(), name="analyze"),
    path("batch/", views.BatchAnalyzeView.as_view(), name="batch"),
    path("health/", views.HealthCheckView.as_view(), name="health"),

    # Cache management
    path("cache/stats/", views.CacheStatsView.as_view(), name="cache-stats"),
    path("cache/clear/", views.CacheClearView.as_view(), name="cache-clear"),
    path("cache/cleanup/", views.CacheCleanupView.as_view(), name="cache-cleanup"),

    # Testing helpers
    path("sample-events/", views.SampleEventsView.as_view(), name="sample-events"),
]

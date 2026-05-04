"""URL routing for the Data Agent API."""
from django.urls import path
from . import views

app_name = 'data_agent'

urlpatterns = [
    path('health/', views.HealthCheckView.as_view(), name='health'),
    path('collect/', views.CollectEventsView.as_view(), name='collect'),
    path('collect-stream/', views.CollectEventsStreamView.as_view(), name='collect-stream'),
    
    # CRITICAL: This is the pipeline endpoint
    path('pipeline-collect/', views.PipelineCollectView.as_view(), name='pipeline-collect'),
    
    path('query/', views.QueryEventsView.as_view(), name='query'),
    path('analyze/', views.AnalyzeEventsView.as_view(), name='analyze'),
    path('inject-attack/', views.InjectAttackView.as_view(), name='inject-attack'),
    path('stats/', views.StatsView.as_view(), name='stats'),
]

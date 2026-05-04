"""URL routing for Attacker Agent API."""
from django.urls import path
from . import views

urlpatterns = [
    # Health check
    path('health/', views.HealthCheckView.as_view(), name='attacker-health'),
    
    # Attack patterns
    path('patterns/', views.ListPatternsView.as_view(), name='attacker-patterns'),
    
    # Attack injection
    path('inject/', views.InjectAttackView.as_view(), name='attacker-inject'),
    
    # Agent control
    path('start/', views.StartAgentView.as_view(), name='attacker-start'),
    path('stop/', views.StopAgentView.as_view(), name='attacker-stop'),
    path('simulate/', views.SimulateAttackView.as_view(), name='attacker-simulate'),
    
    # Statistics and history
    path('stats/', views.StatsView.as_view(), name='attacker-stats'),
    path('history/', views.HistoryView.as_view(), name='attacker-history'),
    path('logs/', views.LogsView.as_view(), name='attacker-logs'),
    
    # A2A behavior analysis result
    path('behavior-result/', views.BehaviorResultView.as_view(), name='attacker-behavior-result'),
]

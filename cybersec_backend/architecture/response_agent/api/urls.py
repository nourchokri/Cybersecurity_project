"""URL routing for Response Agent API."""

from django.urls import path
from .views import (
    HealthCheckView,
    ProcessRiskDecisionView,
    UserApprovalView,
    RLTrainingView,
    RLStatsView,
    TwilioCallbackView,
    TwilioGatherView,
    TwilioStatusView
)

app_name = 'response_agent'

urlpatterns = [
    # Health check
    path('health/', HealthCheckView.as_view(), name='health'),
    
    # Main processing endpoint
    path('process/', ProcessRiskDecisionView.as_view(), name='process'),
    
    # User approval
    path('approval/', UserApprovalView.as_view(), name='approval'),
    
    # RL training
    path('train/', RLTrainingView.as_view(), name='train'),
    path('rl/stats/', RLStatsView.as_view(), name='rl-stats'),
    
    # Twilio callbacks
    path('twilio/callback/', TwilioCallbackView.as_view(), name='twilio-callback'),
    path('twilio/gather/', TwilioGatherView.as_view(), name='twilio-gather'),
    path('twilio/status/', TwilioStatusView.as_view(), name='twilio-status'),
]

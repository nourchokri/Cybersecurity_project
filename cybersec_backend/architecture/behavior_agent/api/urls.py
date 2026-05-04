"""URL routing for the Behavior Analysis Agent API."""

from django.urls import path
from . import views

app_name = 'behavior_agent'

urlpatterns = [
    path('health/',              views.HealthCheckView.as_view(),    name='health'),
    path('score/',               views.ScoreSessionView.as_view(),   name='score'),
    path('batch/',               views.BatchScoreView.as_view(),     name='batch'),
    path('sample-sessions/',     views.SampleSessionsView.as_view(), name='sample-sessions'),
    path('baseline/<str:user_id>/', views.UserBaselineView.as_view(), name='baseline'),
    path('history/<str:user_id>/',  views.UserHistoryView.as_view(),  name='history'),
]
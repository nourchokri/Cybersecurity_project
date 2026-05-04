"""URL routing for Network Analysis endpoints (part of Behavior Agent)."""

from django.urls import path
from . import views

app_name = 'network_agent'

urlpatterns = [
    path('health/',         views.NetworkHealthView.as_view(),  name='network-health'),
    path('analyze/batch/',  views.NetworkBatchView.as_view(),   name='network-batch'),
]

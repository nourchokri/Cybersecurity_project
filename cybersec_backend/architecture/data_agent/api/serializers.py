"""Serializers for Data Agent API."""
from rest_framework import serializers


class CollectRequestSerializer(serializers.Serializer):
    """Request to collect events from specific collectors."""
    collectors = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="List of collector names (e.g., ['file', 'network']). If empty, runs all."
    )


class QueryRequestSerializer(serializers.Serializer):
    """Request to query stored events."""
    start_date = serializers.DateField(required=False, help_text="Start date (YYYY-MM-DD)")
    end_date = serializers.DateField(required=False, help_text="End date (YYYY-MM-DD)")
    event_type = serializers.CharField(required=False, help_text="Filter by event type")
    user_id = serializers.CharField(required=False, help_text="Filter by user ID")
    limit = serializers.IntegerField(default=100, help_text="Max events to return")


class AnalyzeRequestSerializer(serializers.Serializer):
    """Request to analyze events with LLM agent."""
    query = serializers.CharField(required=True, help_text="Analysis query/question")
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    event_type = serializers.CharField(required=False)
    max_events = serializers.IntegerField(default=100)


class InjectAttackSerializer(serializers.Serializer):
    """Request to inject synthetic attack patterns."""
    attack_type = serializers.CharField(required=False, help_text="Specific attack type or random")
    count = serializers.IntegerField(default=1, help_text="Number of attack events to inject")

"""DRF Serializers for the Risk Decision Agent API."""

from rest_framework import serializers


class AnomalyEventSerializer(serializers.Serializer):
    """Validates incoming anomaly events from Team 2 (or frontend)."""

    event_id = serializers.CharField(required=True)
    user_id = serializers.CharField(required=True)
    entity_id = serializers.CharField(required=False, default="", allow_blank=True)
    timestamp = serializers.CharField(required=False, default="")
    # Accept both 'score' and 'combined_score'
    score = serializers.FloatField(required=False, default=0.0)
    combined_score = serializers.FloatField(required=False, default=None, allow_null=True)
    if_score = serializers.FloatField(required=False, default=None, allow_null=True)
    dim_scores = serializers.DictField(required=False, default=None, allow_null=True)
    dimension_scores = serializers.DictField(required=False, default=None, allow_null=True)
    triggered_rules = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    rules = serializers.ListField(
        child=serializers.CharField(), required=False, default=None, allow_null=True
    )
    raw_features = serializers.DictField(required=False, default=None, allow_null=True)
    confidence = serializers.CharField(required=False, default="medium")
    cold_start = serializers.BooleanField(required=False, default=False)
    threat_classification = serializers.CharField(required=False, default="unknown")
    monitor = serializers.CharField(required=False, default=None, allow_null=True, allow_blank=True)
    simulated = serializers.BooleanField(required=False, default=False)


class ContextSummarySerializer(serializers.Serializer):
    asset_sensitivity = serializers.CharField()
    asset_data_type = serializers.CharField()
    recent_incidents = serializers.JSONField()
    triggered_rules_count = serializers.IntegerField()


class DecisionOutputSerializer(serializers.Serializer):
    """Structures the decision output for the frontend / Team 4."""

    event_id = serializers.CharField()
    timestamp = serializers.CharField(allow_null=True, allow_blank=True)
    user_id = serializers.CharField()
    entity_id = serializers.CharField(allow_null=True, allow_blank=True)

    base_score = serializers.FloatField()
    risk_adjustment = serializers.FloatField()
    adjusted_risk_score = serializers.FloatField()
    risk_level = serializers.CharField()  # LOW | MEDIUM | HIGH

    decision = serializers.CharField()  # ALLOW | MONITOR | ESCALATE | BLOCK
    recommended_action = serializers.CharField()

    base_score_analysis = serializers.CharField(allow_blank=True)
    risk_factors = serializers.ListField(child=serializers.CharField())
    mitigating_factors = serializers.ListField(child=serializers.CharField())
    adjustment_reasoning = serializers.CharField(allow_blank=True)
    decision_reasoning = serializers.CharField(allow_blank=True)

    context_summary = ContextSummarySerializer()
    confidence = serializers.CharField()
    computation_method = serializers.CharField(required=False)
    llm_driven = serializers.BooleanField(required=False)
    execution_logs = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class BatchRequestSerializer(serializers.Serializer):
    """Batch analysis request."""

    events = AnomalyEventSerializer(many=True)
    parallel = serializers.IntegerField(required=False, default=1, min_value=1, max_value=8)


class CacheStatsSerializer(serializers.Serializer):
    """Cache statistics output."""

    total_entries = serializers.IntegerField(required=False)
    active_entries = serializers.IntegerField(required=False)
    expired_entries = serializers.IntegerField(required=False)
    db_size_bytes = serializers.IntegerField(required=False)
    db_size_mb = serializers.FloatField(required=False)
    cache_type = serializers.CharField(required=False)

"""DRF Serializers for the Behavior Analysis Agent API."""

from rest_framework import serializers


class SessionInputSerializer(serializers.Serializer):
    """Validates incoming session data for scoring."""

    user_id          = serializers.CharField(required=True)
    pc               = serializers.CharField(required=False, default='', allow_blank=True)
    session_start    = serializers.CharField(required=False, default='')
    hour_of_day      = serializers.IntegerField(required=False, default=9, min_value=0, max_value=23)
    is_weekend       = serializers.IntegerField(required=False, default=0, min_value=0, max_value=1)
    is_outside_hours = serializers.IntegerField(required=False, default=0, min_value=0, max_value=1)
    duration_minutes = serializers.FloatField(required=False, default=60.0, min_value=1.0)
    file_count       = serializers.IntegerField(required=False, default=0, min_value=0)
    max_sensitivity  = serializers.IntegerField(required=False, default=0, min_value=0, max_value=2)
    usb_connected    = serializers.IntegerField(required=False, default=0, min_value=0, max_value=1)
    usb_first_time   = serializers.IntegerField(required=False, default=0, min_value=0, max_value=1)
    email_count      = serializers.IntegerField(required=False, default=0, min_value=0)
    has_ext_email    = serializers.IntegerField(required=False, default=0, min_value=0, max_value=1)
    visited_exfil_domain     = serializers.IntegerField(required=False, default=0, min_value=0, max_value=1)
    visited_jobsearch_domain = serializers.IntegerField(required=False, default=0, min_value=0, max_value=1)
    simulated        = serializers.BooleanField(required=False, default=False)


class BatchSessionSerializer(serializers.Serializer):
    """Batch scoring request."""
    sessions = SessionInputSerializer(many=True)


class DimensionScoresSerializer(serializers.Serializer):
    time        = serializers.FloatField()
    device      = serializers.FloatField()
    volume      = serializers.FloatField()
    sensitivity = serializers.FloatField()


class DetectionAgentAnalysisSerializer(serializers.Serializer):
    model             = serializers.CharField()
    llm_used          = serializers.BooleanField()
    analyst_note      = serializers.CharField()
    scoring_mode      = serializers.CharField()
    score             = serializers.FloatField()
    threshold         = serializers.FloatField()
    verdict           = serializers.CharField()
    triggered_signals = serializers.ListField(child=serializers.CharField())
    dimension_breakdown = DimensionScoresSerializer()
    session_summary   = serializers.DictField()
    baseline_context  = serializers.DictField()


class AnomalyResultSerializer(serializers.Serializer):
    """Structures the AnomalyResult output (Contract 3 schema)."""

    event_id               = serializers.CharField()
    timestamp              = serializers.CharField(allow_blank=True)
    source                 = serializers.ListField(child=serializers.CharField())
    user_anomaly_score     = serializers.FloatField()
    network_anomaly_score  = serializers.FloatField(allow_null=True)
    combined_score         = serializers.FloatField()
    user_id                = serializers.CharField()
    entity_id              = serializers.CharField(allow_null=True)
    dimension_scores       = DimensionScoresSerializer()
    triggered_rules        = serializers.ListField(child=serializers.CharField())
    network_attack_category = serializers.CharField(allow_null=True)
    correlation            = serializers.DictField()
    explanation            = serializers.CharField()
    baseline_age_days      = serializers.IntegerField()
    confidence             = serializers.CharField()
    cold_start             = serializers.BooleanField()
    simulated              = serializers.BooleanField()
    flagged                = serializers.BooleanField()
    if_score               = serializers.FloatField()
    detection_agent_analysis = DetectionAgentAnalysisSerializer()

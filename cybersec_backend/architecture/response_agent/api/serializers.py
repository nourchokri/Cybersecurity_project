"""Serializers for Response Agent API."""

from rest_framework import serializers


class RiskAgentOutputSerializer(serializers.Serializer):
    """Serializer for risk agent output (input to response agent)."""
    event_id = serializers.CharField()
    timestamp = serializers.CharField()
    user_id = serializers.CharField()
    entity_id = serializers.CharField(required=False, allow_blank=True)
    base_score = serializers.FloatField()
    risk_adjustment = serializers.FloatField()
    adjusted_risk_score = serializers.FloatField()
    risk_level = serializers.CharField()
    decision = serializers.CharField()
    recommended_action = serializers.CharField()
    risk_factors = serializers.ListField(child=serializers.CharField())
    mitigating_factors = serializers.ListField(child=serializers.CharField())
    context_summary = serializers.DictField()
    confidence = serializers.CharField()
    computation_method = serializers.CharField(required=False)
    llm_driven = serializers.BooleanField(required=False)
    execution_logs = serializers.ListField(child=serializers.CharField(), required=False)


class DecisionOutputSerializer(serializers.Serializer):
    """Serializer for individual decision output."""
    action = serializers.CharField()
    confidence = serializers.FloatField()
    reasoning = serializers.CharField()
    source = serializers.CharField()


class FinalDecisionSerializer(serializers.Serializer):
    """Serializer for final decision output."""
    event_id = serializers.CharField()
    user_id = serializers.CharField()
    timestamp = serializers.CharField()
    risk_level = serializers.CharField()
    final_action = serializers.CharField()
    execution_status = serializers.CharField()
    
    llm_weighted_decision = DecisionOutputSerializer()
    llm_direct_decision = DecisionOutputSerializer()
    rl_decision = DecisionOutputSerializer()
    
    orchestrator_reasoning = serializers.CharField()
    confidence = serializers.FloatField()
    
    risk_explanation = serializers.CharField()
    action_explanation = serializers.CharField()
    
    user_approval_required = serializers.BooleanField()
    user_approval_status = serializers.CharField(required=False, allow_null=True)
    twilio_call_sid = serializers.CharField(required=False, allow_null=True)


class UserApprovalSerializer(serializers.Serializer):
    """Serializer for user approval callback."""
    event_id = serializers.CharField()
    user_response = serializers.CharField()  # "1" for approve, "2" for deny
    risk_data = RiskAgentOutputSerializer()
    action = serializers.CharField()


class RLTrainingSerializer(serializers.Serializer):
    """Serializer for RL model training."""
    event_id = serializers.CharField()
    risk_data = RiskAgentOutputSerializer()
    action_taken = serializers.CharField()
    outcome = serializers.ChoiceField(choices=["SUCCESS", "FALSE_POSITIVE", "FALSE_NEGATIVE", "INCIDENT"])

"""DRF Serializers for Attacker Agent API."""
from rest_framework import serializers


class InjectAttackSerializer(serializers.Serializer):
    """Serializer for attack injection requests."""
    
    attack_id = serializers.CharField(
        required=True,
        help_text="Attack pattern ID (e.g., 'cert_r42_s1_aam0658')"
    )
    user_id = serializers.CharField(
        required=False,
        help_text="User ID for attack simulation"
    )
    device_id = serializers.CharField(
        required=False,
        help_text="Device ID for attack simulation"
    )
    is_simulated = serializers.BooleanField(
        default=True,
        help_text="Mark events as simulated (always True)"
    )


class StartAgentSerializer(serializers.Serializer):
    """Serializer for starting the adversarial agent."""
    
    interval_seconds = serializers.IntegerField(
        default=600,
        min_value=60,
        max_value=3600,
        help_text="Attack interval in seconds (60-3600)"
    )
    max_attacks = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text="Maximum number of attacks to inject (optional)"
    )


class ListPatternsSerializer(serializers.Serializer):
    """Serializer for listing attack patterns."""
    
    category = serializers.ChoiceField(
        choices=[
            'data_exfiltration',
            'credential_theft',
            'sabotage',
            'policy_violation',
            'reconnaissance'
        ],
        required=False,
        help_text="Filter by attack category"
    )
    severity = serializers.ChoiceField(
        choices=['low', 'medium', 'high', 'critical'],
        required=False,
        help_text="Filter by severity level"
    )

"""Django app configuration for Attacker Agent."""
from django.apps import AppConfig


class AttackerAgentConfig(AppConfig):
    """Configuration for the Attacker Agent Django app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'architecture.attacker_agent'
    verbose_name = 'Attacker Agent'
    
    def ready(self):
        """Initialize the attacker agent when Django starts."""
        # Import here to avoid circular imports
        pass

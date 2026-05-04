"""Django app configuration for Data Agent."""
from django.apps import AppConfig


class DataAgentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'architecture.data_agent'
    verbose_name = 'Data Exfiltration Agent'

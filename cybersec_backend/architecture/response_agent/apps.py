"""Django app configuration for Response Agent."""

from django.apps import AppConfig


class ResponseAgentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'architecture.response_agent'
    verbose_name = 'Response Agent'

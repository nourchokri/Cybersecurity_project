from django.apps import AppConfig


class BehaviorAgentConfig(AppConfig):
    name = 'architecture.behavior_agent'
    verbose_name = 'Behavior Analysis Agent'

    def ready(self):
        # Warm baseline cache and pre-load IF model on startup
        try:
            from .application.cache import warm_cache
            warm_cache()
            from .scoring.model import _load
            _load()
        except Exception as e:
            import logging
            logging.getLogger('behavior_agent').warning(
                f'Startup warm-up failed (non-fatal): {e}'
            )

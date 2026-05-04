"""Development settings."""

from .base import *  # noqa: F401,F403

DEBUG = True

# Allow all origins during development (Next.js dev server)
CORS_ALLOW_ALL_ORIGINS = True

# Show browsable API in dev
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "architecture": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

"""
Django base settings for cybersec_backend.

Shared across dev / prod. Environment-specific overrides live in dev.py / prod.py.
"""

from pathlib import Path

import environ

# ── Paths ──────────────────────────────────────────────────────────────────────
# BASE_DIR = cybersec_backend/
BASE_DIR = Path(__file__).resolve().parents[2]

# ── Environment ────────────────────────────────────────────────────────────────
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["*"]),
)
environ.Env.read_env(str(BASE_DIR / ".env"))

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ── Application definition ────────────────────────────────────────────────────
INSTALLED_APPS = [
    # Django built-ins
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    # Project apps — agents
    "architecture.risk_decision_agent",
    "architecture.behavior_agent",
    "architecture.data_agent",
    "architecture.attacker_agent",  # NEW: Attacker Agent
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ── Database ───────────────────────────────────────────────────────────────────
# Django ORM uses SQLite (lightweight). CERT tools query Supabase directly via
# psycopg — they do NOT go through Django ORM.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ── REST Framework ─────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
}

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ── Static files ──────────────────────────────────────────────────────────────
STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Project-specific settings ─────────────────────────────────────────────────
# These are read by the risk_decision_agent orchestration layer.
SUPABASE_DB_URL = env("SUPABASE_DB_URL", default="")

# ── Behavior Agent (Monitor A) settings ───────────────────────────────────────
# URL of Team 3's Risk Decision Agent (for forwarding flagged events)
RISK_AGENT_URL = env(
    "RISK_AGENT_URL",
    default="http://127.0.0.1:8000/api/v1/risk-decision/analyze/"
)
# Enable/disable automatic forwarding to Team 3 (useful for testing/debugging)
ENABLE_RISK_AGENT_FORWARDING = env("ENABLE_RISK_AGENT_FORWARDING", default=True, cast=bool)
# Detection threshold — IF-only mode: 0.4 gives 98% recall
BEHAVIOR_ANOMALY_THRESHOLD = env("BEHAVIOR_ANOMALY_THRESHOLD", default=0.4, cast=float)
ANOMALY_THRESHOLD = BEHAVIOR_ANOMALY_THRESHOLD  # alias used by monitor_a code

# LLM for explanation generation (same server as risk agent)
ESPRIT_API_KEY  = env("ESPRIT_API_KEY",  default="")
ESPRIT_BASE_URL = env("ESPRIT_BASE_URL", default="https://tokenfactory.esprit.tn/api")
ESPRIT_MODEL    = env("ESPRIT_MODEL",    default="hosted_vllm/Llama-3.1-70B-Instruct")

# ── Behavior Agent model file paths ──────────────────────────────────────────
# All model files and data are now organized within the Django project structure
DATA_DIR = BASE_DIR / 'data'

IF_MODEL_PATH      = DATA_DIR / 'if_model_A.pkl'
FEAT_COLS_PATH     = DATA_DIR / 'feature_cols_A.pkl'
SCORE_BOUNDS_PATH  = DATA_DIR / 'score_bounds_A.pkl'
BASELINES_DB       = DATA_DIR / 'baselines.sqlite'
TEST_SESSIONS_PATH = DATA_DIR / 'test_sessions.parquet'
INSIDERS_CSV_PATH  = DATA_DIR / 'insiders.csv'
AGENT_MEMORY_DB    = DATA_DIR / 'agent_memory.db'
ANOMALY_THRESHOLD  = BEHAVIOR_ANOMALY_THRESHOLD

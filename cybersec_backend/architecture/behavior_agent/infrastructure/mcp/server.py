"""
MCP server for Behavior Agent.

Exposes behavioral scoring tools over the Model Context Protocol (stdio).
Mirrors the pattern used by the Risk Decision Agent's MCP server.

Run as subprocess by the MCP client:
  python architecture/behavior_agent/infrastructure/mcp/server.py

Tools exposed:
  behavior.baseline.get_user_baseline     — UserBaseline stats for a user
  behavior.baseline.get_user_history      — Recent session scores and trend
  behavior.baseline.get_dept_stats        — Department-level behavioral norms
  behavior.session.score_session          — Full IF scoring pipeline
  behavior.session.get_feature_vector     — 18-feature vector for a session
  behavior.rules.explain_triggered_rules  — Human-readable rule explanations
  behavior.policy.get_thresholds          — Detection thresholds and config
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Allow absolute imports from the Django project root when run as subprocess
_PROJECT_ROOT = str(Path(__file__).resolve().parents[4])  # cybersec_backend/
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Bootstrap Django settings before importing any Django-dependent modules
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

import django
django.setup()

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("behavior_agent_tools")


def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


# ── Tool 1: Get user baseline ─────────────────────────────────────────────────

@mcp.tool(name="behavior.baseline.get_user_baseline")
def get_user_baseline(user_id: str) -> str:
    """
    Return the behavioral baseline for a user.
    Includes login hour stats, file volume stats, known devices, department.
    """
    from architecture.behavior_agent.application.cache import get_cached_baseline
    b = get_cached_baseline(user_id)
    if b is None:
        return _json({'error': f'No baseline found for user {user_id}'})
    return _json({
        'user_id':              b.user_id,
        'department':           b.department,
        'observation_days':     b.observation_days,
        'cold_start':           b.cold_start,
        'login_hour_mean':      round(b.login_hour_mean, 2),
        'login_hour_std':       round(b.login_hour_std, 2),
        'file_access_mean':     round(b.daily_file_access_mean, 2),
        'file_access_std':      round(b.daily_file_access_std, 2),
        'email_mean':           round(b.daily_email_mean, 2),
        'known_devices_count':  len(b.known_devices),
        'known_devices':        b.known_devices[:5],
        'role_sensitivity_ceiling': b.role_sensitivity_ceiling,
        'typical_max_sensitivity':  b.typical_max_sensitivity,
        'dept_file_mean':       round(b.dept_file_access_mean, 2),
        'dept_email_mean':      round(b.dept_email_mean, 2),
        'dept_login_hour_mean': round(b.dept_login_hour_mean, 2),
        'dept_usb_rate':        round(b.dept_usb_rate, 3),
    })


# ── Tool 2: Get user history ──────────────────────────────────────────────────

@mcp.tool(name="behavior.baseline.get_user_history")
def get_user_history(user_id: str, limit: int = 7) -> str:
    """
    Return recent session scores and trend for a user.
    Useful for detecting escalating anomaly patterns.
    """
    from architecture.behavior_agent.application.cache import get_cached_baseline
    from architecture.behavior_agent.scoring.features import compute_score_trend
    from architecture.behavior_agent.memory.checkpointer import get_user_history as _get_history

    b = get_cached_baseline(user_id)
    recent_scores = b.recent_scores if b else []
    trend = compute_score_trend(recent_scores)

    db_history = _get_history(user_id, limit=limit)

    return _json({
        'user_id':       user_id,
        'recent_scores': recent_scores,
        'score_trend':   round(trend, 4),
        'trend_label':   'escalating' if trend > 0.05 else ('declining' if trend < -0.05 else 'stable'),
        'session_history': db_history,
    })


# ── Tool 3: Get department stats ──────────────────────────────────────────────

@mcp.tool(name="behavior.baseline.get_dept_stats")
def get_dept_stats(user_id: str) -> str:
    """
    Return department-level behavioral norms for a user's department.
    Used as peer comparison reference.
    """
    from architecture.behavior_agent.application.cache import get_cached_baseline
    b = get_cached_baseline(user_id)
    if b is None:
        return _json({'error': f'No baseline for {user_id}'})
    return _json({
        'department':           b.department,
        'dept_file_mean':       round(b.dept_file_access_mean, 2),
        'dept_file_std':        round(b.dept_file_access_std, 2),
        'dept_email_mean':      round(b.dept_email_mean, 2),
        'dept_email_std':       round(b.dept_email_std, 2),
        'dept_login_hour_mean': round(b.dept_login_hour_mean, 2),
        'dept_login_hour_std':  round(b.dept_login_hour_std, 2),
        'dept_usb_rate':        round(b.dept_usb_rate, 3),
    })


# ── Tool 4: Score a session ───────────────────────────────────────────────────

@mcp.tool(name="behavior.session.score_session")
def score_session(session_json: str) -> str:
    """
    Run the full Behavior Agent scoring pipeline on a session dict.
    Returns IF score, dimension scores, triggered rules, and verdict.
    Input: JSON string of session dict.
    """
    session = json.loads(session_json)
    user_id = session.get('user_id', '')

    from architecture.behavior_agent.application.cache import get_cached_baseline
    from architecture.behavior_agent.scoring.baseline import UserBaseline
    from architecture.behavior_agent.scoring.features import extract_user_features
    from architecture.behavior_agent.scoring.model import run_IF_model_A
    from architecture.behavior_agent.scoring.dimensions import dim_scorer
    from django.conf import settings

    b = get_cached_baseline(user_id)
    if b is None:
        return _json({'error': f'No baseline for {user_id}'})

    features = extract_user_features(session, b)
    if_score = run_IF_model_A(features)
    dims     = dim_scorer(session, b)
    threshold = getattr(settings, 'ANOMALY_THRESHOLD', 0.4)

    verdict = (
        'CRITICAL' if if_score >= 0.8 else
        'HIGH'     if if_score >= 0.6 else
        'MEDIUM'   if if_score >= threshold else
        'LOW'
    )

    return _json({
        'user_id':         user_id,
        'if_score':        round(if_score, 4),
        'final_score':     round(if_score, 4),
        'flagged':         if_score >= threshold,
        'verdict':         verdict,
        'threshold':       threshold,
        'dim_time':        round(dims['time'], 4),
        'dim_device':      round(dims['device'], 4),
        'dim_volume':      round(dims['volume'], 4),
        'dim_sensitivity': round(dims['sensitivity'], 4),
        'triggered_rules': dims['triggered_rules'],
    })


# ── Tool 5: Get feature vector ────────────────────────────────────────────────

@mcp.tool(name="behavior.session.get_feature_vector")
def get_feature_vector(session_json: str) -> str:
    """
    Compute and return the 18-feature vector for a session.
    Useful for understanding what the IF model sees.
    Input: JSON string of session dict.
    """
    session = json.loads(session_json)
    user_id = session.get('user_id', '')

    from architecture.behavior_agent.application.cache import get_cached_baseline
    from architecture.behavior_agent.scoring.features import extract_user_features

    b = get_cached_baseline(user_id)
    if b is None:
        return _json({'error': f'No baseline for {user_id}'})

    features = extract_user_features(session, b)
    return _json({'user_id': user_id, 'features': {k: round(v, 4) for k, v in features.items()}})


# ── Tool 6: Explain triggered rules ──────────────────────────────────────────

RULE_EXPLANATIONS = {
    'login_outside_normal_hours': (
        'User logged in at an unusual hour relative to their historical pattern. '
        'Circular distance from mean login hour exceeds 4 standard deviations.'
    ),
    'unknown_device': (
        'Login from a workstation not seen during the 60-day training period. '
        'Could indicate account compromise or unauthorized access.'
    ),
    'file_download_volume_extreme': (
        'File access count is more than 8 standard deviations above the user\'s baseline mean. '
        'Consistent with mass data exfiltration (Scenario 1: WikiLeaks pattern).'
    ),
    'high_sensitivity_file_access': (
        'User accessed files above their normal sensitivity ceiling or typical maximum. '
        'May indicate privilege escalation or unauthorized data access.'
    ),
    'usb_device_connected': (
        'A USB removable device was connected during this session. '
        'Combined with other signals, may indicate data exfiltration via removable media.'
    ),
    'usb_first_time': (
        'This is the first USB connection ever recorded for this user. '
        'Strong Scenario 1 signal — normal users rarely connect USB for the first time suddenly.'
    ),
    'external_email_recipient': (
        'Email sent to a recipient outside the corporate domain (@dtaa.com). '
        'May indicate pre-resignation data sharing (Scenario 2: IP Theft pattern).'
    ),
    'exfil_domain_visited': (
        'User visited wikileaks.org during this session. '
        'Definitive Scenario 1 signal — this domain was absent from all training data.'
    ),
    'jobsearch_domain_visited': (
        'User visited a job search site (LinkedIn, Monster, CareerBuilder, Indeed, Glassdoor). '
        'Scenario 2 signal — indicates pre-resignation behavior.'
    ),
}


@mcp.tool(name="behavior.rules.explain_triggered_rules")
def explain_triggered_rules(rule_ids: List[str]) -> str:
    """
    Return human-readable explanations for a list of triggered rule IDs.
    """
    explanations = {}
    for rule_id in rule_ids:
        explanations[rule_id] = RULE_EXPLANATIONS.get(
            rule_id,
            f'Rule {rule_id}: anomalous behavior detected relative to user baseline.'
        )
    return _json({'explanations': explanations})


# ── Tool 7: Get policy thresholds ─────────────────────────────────────────────

@mcp.tool(name="behavior.policy.get_thresholds")
def get_thresholds() -> str:
    """
    Return the current detection thresholds and scoring configuration.
    """
    from django.conf import settings
    return _json({
        'anomaly_threshold':  getattr(settings, 'ANOMALY_THRESHOLD', 0.4),
        'scoring_mode':       'IF-only',
        'update_threshold':   0.4,
        'verdicts': {
            'LOW':      f'score < {getattr(settings, "ANOMALY_THRESHOLD", 0.4)}',
            'MEDIUM':   f'{getattr(settings, "ANOMALY_THRESHOLD", 0.4)} <= score < 0.6',
            'HIGH':     '0.6 <= score < 0.8',
            'CRITICAL': 'score >= 0.8',
        },
        'recall_at_threshold': {
            '0.3': '100% (49/49 malicious users)',
            '0.4': '98%  (48/49 malicious users)',
            '0.5': '88%  (43/49 malicious users)',
        },
        'model': 'IsolationForest(n_estimators=200, contamination=0.1)',
        'features': 18,
    })


def main() -> None:
    mcp.run()


if __name__ == '__main__':
    main()
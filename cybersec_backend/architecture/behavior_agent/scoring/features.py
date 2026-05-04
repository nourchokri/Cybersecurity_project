"""
Feature extraction: converts a closed session dict + UserBaseline
into the 18-float vector expected by the IF model.
"""
import math
import numpy as np


def circular_distance(hour: float, mean_hour: float) -> float:
    diff = abs(hour - mean_hour) % 24
    return min(diff, 24 - diff)


def compute_score_trend(scores: list) -> float:
    if len(scores) < 2:
        return 0.0
    n = len(scores)
    x = list(range(n))
    x_mean = sum(x) / n
    y_mean = sum(scores) / n
    num = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, scores))
    den = sum((xi - x_mean) ** 2 for xi in x)
    if den == 0:
        return 0.0
    return float(max(-1.0, min(1.0, num / den)))


def extract_user_features(session: dict, baseline) -> dict:
    """
    Build the 18-feature vector from a session dict and its UserBaseline.
    All values are floats. NaN/inf are handled by the model loader.
    """
    hour       = session['hour_of_day']
    file_count = session['file_count']
    dur        = max(session.get('duration_minutes', 1.0), 1.0)
    f_std      = max(baseline.daily_file_access_std, 1.0)
    f_mean     = baseline.daily_file_access_mean
    d_std      = max(baseline.dept_file_access_std, 1.0)
    d_mean     = baseline.dept_file_access_mean

    return {
        'hour_of_day':              float(hour),
        'hour_deviation':           circular_distance(hour, baseline.login_hour_mean),
        'is_weekend':               float(session.get('is_weekend', 0)),
        'is_outside_hours':         float(session.get('is_outside_hours', 0)),
        'is_new_device':            float(
            session.get('pc', '') not in set(baseline.known_devices)
            if session.get('pc') else 0
        ),
        'file_count':               float(file_count),
        'file_count_zscore':        (file_count - f_mean) / f_std,
        'files_per_minute':         file_count / dur,
        'max_sensitivity':          float(session.get('max_sensitivity', 0)),
        'sensitivity_above_ceil':   float(
            session.get('max_sensitivity', 0) > baseline.role_sensitivity_ceiling
        ),
        'email_count':              float(session.get('email_count', 0)),
        'has_ext_email':            float(session.get('has_ext_email', 0)),
        'usb_connected':            float(session.get('usb_connected', 0)),
        'usb_first_time':           float(session.get('usb_first_time', 0)),
        'visited_exfil_domain':     float(session.get('visited_exfil_domain', 0)),
        'visited_jobsearch_domain': float(session.get('visited_jobsearch_domain', 0)),
        'recent_score_trend':       compute_score_trend(baseline.recent_scores),
        'file_count_peer_zscore':   (file_count - d_mean) / d_std,
    }
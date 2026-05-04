"""
Dimension scorers and score aggregation.
Equal-weight formula: S_A = mean(IF, time, device, volume, sensitivity)
Floor rule: if 2+ dimensions >= 1.0 then S_A >= 0.6
"""
import numpy as np
from .features import circular_distance


def score_time(session: dict, baseline) -> float:
    dist = circular_distance(session['hour_of_day'], baseline.login_hour_mean)
    return float(min(dist / max(baseline.login_hour_std, 0.5) / 8.0, 1.0))


def score_device(session: dict, baseline) -> float:
    pc = session.get('pc', '')
    return 1.0 if pc and pc not in set(baseline.known_devices) else 0.0


def score_volume(session: dict, baseline) -> float:
    """Saturation at Z=8 to reduce false positives from zero-inflated baselines."""
    z = (session['file_count'] - baseline.daily_file_access_mean) / max(baseline.daily_file_access_std, 1.0)
    return 0.0 if z <= 0 else float(min(z / 8.0, 1.0))


def score_sensitivity(session: dict, baseline) -> float:
    obs = session.get('max_sensitivity', 0)
    if obs > baseline.role_sensitivity_ceiling:
        return 1.0
    if obs > baseline.typical_max_sensitivity:
        return 0.5
    return 0.0


def dim_scorer(session: dict, baseline) -> dict:
    s_t = score_time(session, baseline)
    s_d = score_device(session, baseline)
    s_v = score_volume(session, baseline)
    s_s = score_sensitivity(session, baseline)

    triggered = []
    if s_t > 0.5:                              triggered.append('login_outside_normal_hours')
    if s_d > 0.0:                              triggered.append('unknown_device')
    if s_v > 0.5:                              triggered.append('file_download_volume_extreme')
    if s_s > 0.0:                              triggered.append('high_sensitivity_file_access')
    if session.get('usb_connected'):           triggered.append('usb_device_connected')
    if session.get('has_ext_email'):           triggered.append('external_email_recipient')
    if session.get('visited_exfil_domain'):    triggered.append('exfil_domain_visited')
    if session.get('visited_jobsearch_domain'):triggered.append('jobsearch_domain_visited')
    if session.get('usb_first_time'):          triggered.append('usb_first_time')

    return {
        'time': s_t, 'device': s_d,
        'volume': s_v, 'sensitivity': s_s,
        'triggered_rules': triggered,
    }


def aggregate_scores(if_score: float, dim_scores: dict) -> float:
    """
    Equal-weight aggregation — no fixed coefficients.
    Each of the 5 components contributes 20%.
    Floor rule fires only when 2+ dimensions are at maximum.
    """
    components = [
        if_score,
        dim_scores['time'],
        dim_scores['device'],
        dim_scores['volume'],
        dim_scores['sensitivity'],
    ]
    combined = sum(components) / len(components)

    dims_at_max = sum(
        1 for k in ['time', 'device', 'volume', 'sensitivity']
        if dim_scores[k] >= 1.0
    )
    if dims_at_max >= 2:
        combined = max(combined, 0.6)

    return float(np.clip(combined, 0.0, 1.0))
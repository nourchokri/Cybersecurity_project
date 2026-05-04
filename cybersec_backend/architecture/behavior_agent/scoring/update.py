"""
Score-gated baseline update.
Behavioral stats only update when final_score < UPDATE_THRESHOLD (0.4).
recent_scores and observation_days always update.
"""
import math
import numpy as np
from .baseline import save_baseline, load_baseline

UPDATE_THRESHOLD = 0.4


def circular_mean(hours: list) -> float:
    if not hours:
        return 9.0
    angles = [h * 2 * math.pi / 24 for h in hours]
    result = (math.atan2(np.mean(np.sin(angles)),
                         np.mean(np.cos(angles))) * 24 / (2 * math.pi)) % 24
    return float(result if result < 24.0 else 0.0)


def circular_std(hours: list) -> float:
    if len(hours) < 2:
        return 4.0
    angles = [h * 2 * math.pi / 24 for h in hours]
    R = min(math.sqrt(np.mean(np.sin(angles)) ** 2 +
                      np.mean(np.cos(angles)) ** 2), 0.9999)
    return float(math.sqrt(-2 * math.log(R)) * 24 / (2 * math.pi))


def update_baseline(user_id: str, session: dict, conn, final_score: float):
    """
    Update UserBaseline after scoring.
    MUST be called after scoring, never before.
    """
    import pandas as pd
    b = load_baseline(conn, user_id)
    if b is None:
        return

    # Always update
    b.recent_scores.append(float(final_score))
    if len(b.recent_scores) > 7:
        b.recent_scores = b.recent_scores[-7:]
    b.observation_days += 1
    if b.observation_days >= 5:
        b.cold_start = False

    # Gated update — only for normal sessions
    if final_score < UPDATE_THRESHOLD:
        b.login_hours_observed.append(session.get('hour_of_day', 9))
        if len(b.login_hours_observed) > 240:
            b.login_hours_observed = b.login_hours_observed[-240:]
        b.login_hour_mean = circular_mean(b.login_hours_observed)
        b.login_hour_std  = circular_std(b.login_hours_observed)

        b.daily_volume_history.append(float(session.get('file_count', 0)))
        if len(b.daily_volume_history) > 30:
            b.daily_volume_history = b.daily_volume_history[-30:]
        b.daily_file_access_mean = float(np.mean(b.daily_volume_history))
        b.daily_file_access_std  = max(float(np.std(b.daily_volume_history)), 1.0)

        pc = session.get('pc', '')
        if pc and pc not in b.known_devices:
            b.known_devices.append(pc)

    b.last_updated = str(pd.Timestamp.now().date())
    save_baseline(conn, b)
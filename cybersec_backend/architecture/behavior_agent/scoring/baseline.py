"""
UserBaseline dataclass and SQLite persistence helpers.
"""
import sqlite3
import json
import math
import numpy as np
from dataclasses import dataclass, asdict
from django.conf import settings


@dataclass
class UserBaseline:
    user_id:                  str
    last_updated:             str
    observation_days:         int
    cold_start:               bool
    login_hour_mean:          float
    login_hour_std:           float
    login_hours_observed:     list
    known_devices:            list
    daily_file_access_mean:   float
    daily_file_access_std:    float
    daily_volume_history:     list
    typical_max_sensitivity:  int
    role_sensitivity_ceiling: int
    daily_email_mean:         float
    daily_email_std:          float
    department:               str
    feature_history:          list
    recent_scores:            list
    dept_file_access_mean:    float
    dept_file_access_std:     float
    dept_email_mean:          float
    dept_email_std:           float
    dept_login_hour_mean:     float
    dept_login_hour_std:      float
    dept_usb_rate:            float


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(str(settings.BASELINES_DB))


def load_baseline(conn: sqlite3.Connection, user_id: str):
    row = conn.execute(
        'SELECT data FROM baselines WHERE user_id=?', (user_id,)
    ).fetchone()
    if row is None:
        return None
    return UserBaseline(**json.loads(row[0]))


def save_baseline(conn: sqlite3.Connection, b: UserBaseline):
    conn.execute(
        'INSERT OR REPLACE INTO baselines (user_id, data) VALUES (?,?)',
        (b.user_id, json.dumps(asdict(b)))
    )
    conn.commit()
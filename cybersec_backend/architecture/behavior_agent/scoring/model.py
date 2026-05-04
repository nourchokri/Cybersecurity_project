"""
Loads the trained IF model and provides the run_IF_model_A inference function.
Model files are loaded lazily on first use so the app starts without them.
"""
import joblib
import numpy as np

_model     = None
_feat_cols = None
_RAW_MIN   = None
_RAW_MAX   = None


def _load():
    global _model, _feat_cols, _RAW_MIN, _RAW_MAX
    if _model is not None:
        return
    from django.conf import settings
    _model     = joblib.load(settings.IF_MODEL_PATH)
    _feat_cols = joblib.load(settings.FEAT_COLS_PATH)
    bounds     = joblib.load(settings.SCORE_BOUNDS_PATH)
    _RAW_MIN   = bounds['raw_min']
    _RAW_MAX   = bounds['raw_max']


def run_IF_model_A(features: dict) -> float:
    """Score one session. Returns float in [0,1] where 1 = most anomalous."""
    _load()
    X = np.array([[features.get(col, 0.0) for col in _feat_cols]], dtype=float)
    X = np.nan_to_num(X, nan=0.0, posinf=100.0, neginf=-100.0)
    raw = _model.score_samples(X)[0]
    return float(np.clip(1.0 - (raw - _RAW_MIN) / (_RAW_MAX - _RAW_MIN), 0.0, 1.0))


def get_feature_cols() -> list:
    _load()
    return list(_feat_cols)
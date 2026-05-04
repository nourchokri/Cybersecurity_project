"""
Loads your 3 model files once at startup and runs the hybrid pipeline.
Stage 1 — Isolation Forest  (anomaly detection)
Stage 2 — CatBoost          (attack confirmation)
"""
import os
import logging
import numpy as np
import joblib
from catboost import CatBoostClassifier

logger = logging.getLogger(__name__)

HERE     = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(HERE, "..", "..", "..", "data")

SCALER_PATH = os.path.join(DATA_DIR, "my_scaler.pkl")
ISO_PATH    = os.path.join(DATA_DIR, "stage1_iso.pkl")
CAT_PATH    = os.path.join(DATA_DIR, "stage2_catboost.cbm")

_scaler = None
_iso    = None
_cat    = None

def _get_scaler():
    global _scaler
    if _scaler is None:
        _scaler = joblib.load(SCALER_PATH)
        logger.info("Network scaler loaded")
    return _scaler

def _get_iso():
    global _iso
    if _iso is None:
        _iso = joblib.load(ISO_PATH)
        logger.info("Network IF loaded")
    return _iso

def _get_cat():
    global _cat
    if _cat is None:
        _cat = CatBoostClassifier()
        _cat.load_model(CAT_PATH)
        logger.info("Network CatBoost loaded")
    return _cat

def predict(features: np.ndarray) -> dict:
    """
    Input:  np.array shape (34,) — raw features from network_features.py
    Output: dict with all scores and flags
    """
    scaled = _get_scaler().transform(features.reshape(1, -1))

    # Stage 1 — Isolation Forest
    iso_pred  = _get_iso().predict(scaled)[0]       # 1=normal, -1=anomaly
    iso_score = _get_iso().score_samples(scaled)[0]
    anomaly_score = float(np.clip(1.0 - (iso_score + 0.5), 0.0, 1.0))

    # Stage 2 — CatBoost
    cat_prob = float(_get_cat().predict_proba(scaled)[0][1])
    cat_pred = int(_get_cat().predict(scaled)[0])

    # Combined — CatBoost weighted higher (supervised, more precise)
    combined = round((anomaly_score * 0.4) + (cat_prob * 0.6), 4)

    return {
        "anomaly_score":  round(anomaly_score, 4),
        "cat_prob":       round(cat_prob, 4),
        "cat_pred":       cat_pred,
        "stage1_flagged": iso_pred == -1,
        "combined_score": combined,
        "flagged":        combined >= 0.40 or (iso_pred == -1 and cat_pred == 1),
    }
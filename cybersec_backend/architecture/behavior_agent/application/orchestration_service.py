"""
Orchestration Service for the Behavior Analysis Agent.

Manages singleton instances of the LangGraph graph and baseline cache per process.
Uses the organized behavior_agent module structure within the Django project.
"""

from __future__ import annotations

import logging
import threading
import traceback
from typing import Any, Dict, List, Optional

logger = logging.getLogger('behavior_agent')

_lock = threading.Lock()
_service_instance: Optional['BehaviorOrchestrationService'] = None


def get_orchestration_service() -> 'BehaviorOrchestrationService':
    """Return a process-global BehaviorOrchestrationService singleton."""
    global _service_instance
    if _service_instance is not None:
        return _service_instance
    with _lock:
        if _service_instance is not None:
            return _service_instance
        _service_instance = BehaviorOrchestrationService()
        return _service_instance


class BehaviorOrchestrationService:
    """Glue between the DRF API layer and the Behavior Agent domain logic."""

    def __init__(self):
        # Import and initialise the LangGraph graph
        from ..core.graph import graph
        from .cache import warm_cache, cache_size
        from ..scoring.model import _load as load_model

        load_model()
        warm_cache()
        self._graph = graph
        logger.info(
            f'BehaviorOrchestrationService initialized '
            f'(behavior_agent, baselines={cache_size()})'
        )

    # ── Public API ────────────────────────────────────────────────────────

    def score_session(
        self,
        session_data: Dict[str, Any],
        thread_id: str = 'api_default',
    ) -> Dict[str, Any]:
        """Score a single session and return the AnomalyResult."""
        try:
            state = _build_initial_state(session_data)
            config = {'configurable': {'thread_id': thread_id}}
            result = self._graph.invoke(state, config=config)
            ar = result.get('anomaly_result', {})

            if ar.get('error'):
                return {'ok': False, 'error': ar['error']}

            # Persist to session history
            try:
                from ..memory.checkpointer import save_session_result
                save_session_result(thread_id, ar)
            except Exception:
                pass

            return {'ok': True, 'anomaly_result': ar}

        except Exception as e:
            logger.exception('Error scoring session %s', session_data.get('user_id'))
            return {
                'ok': False,
                'error': f'{type(e).__name__}: {e}',
                'traceback': traceback.format_exc().rstrip(),
            }

    def score_batch(
        self,
        sessions: List[Dict[str, Any]],
        thread_id: str = 'api_batch',
    ) -> List[Dict[str, Any]]:
        """Score multiple sessions sequentially."""
        return [
            self.score_session(s, thread_id=f'{thread_id}_{i}')
            for i, s in enumerate(sessions)
        ]

    def get_user_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Return recent session history for a user."""
        try:
            from ..memory.checkpointer import get_user_history
            return get_user_history(user_id, limit=limit)
        except Exception:
            return []

    def get_baseline(self, user_id: str) -> Dict[str, Any]:
        """Return the behavioral baseline for a user."""
        try:
            from .cache import get_cached_baseline
            from dataclasses import asdict
            b = get_cached_baseline(user_id)
            if b is None:
                return {'error': f'No baseline for {user_id}'}
            return asdict(b)
        except Exception as e:
            return {'error': str(e)}

    def health(self) -> Dict[str, Any]:
        """Return health status."""
        try:
            from .cache import cache_size
            from ..scoring.model import get_feature_cols
            return {
                'status': 'ok',
                'baselines_cached': cache_size(),
                'features': len(get_feature_cols()),
                'scoring_mode': 'IF-only',
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_initial_state(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build the initial AgentState from a session dict."""
    # Normalise session_start to string
    session = dict(session_data)
    if hasattr(session.get('session_start'), 'isoformat'):
        session['session_start'] = session['session_start'].isoformat()
    elif 'session_start' not in session:
        session['session_start'] = ''

    return {
        'session':         session,
        'baseline':        None,
        'features':        None,
        'if_score':        None,
        'dim_scores':      None,
        'final_score':     None,
        'triggered_rules': None,
        'explanation':     None,
        'anomaly_result':  None,
        'error':           None,
    }

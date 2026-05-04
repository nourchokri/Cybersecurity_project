"""Client for communicating with the Behavior Agent (Team 2 — Monitor A).

Fetches anomaly events from the Behavior Analysis Agent's REST API.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class BehaviorAgentClient:
    """Fetches anomaly events from the Behavior Agent (Monitor A)."""

    def __init__(self, base_url: str = 'http://127.0.0.1:8000/api/v1/behavior'):
        self.base_url = base_url.rstrip('/')

    def get_latest_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch the latest scored sessions from the Behavior Agent."""
        try:
            import httpx
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f'{self.base_url}/history/recent/', params={'limit': limit})
                resp.raise_for_status()
                return resp.json().get('history', [])
        except Exception as e:
            logger.warning(f'BehaviorAgentClient.get_latest_events failed: {e}')
            return []

    def get_event(self, event_id: str) -> Dict[str, Any]:
        """Fetch a specific event by ID."""
        try:
            import httpx
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f'{self.base_url}/score/{event_id}/')
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.warning(f'BehaviorAgentClient.get_event failed: {e}')
            return {}

    def score_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Request scoring of a session from the Behavior Agent."""
        try:
            import httpx
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(f'{self.base_url}/score/', json=session_data)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.warning(f'BehaviorAgentClient.score_session failed: {e}')
            return {'error': str(e)}

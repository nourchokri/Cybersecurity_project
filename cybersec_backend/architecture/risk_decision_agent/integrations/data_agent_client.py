"""Client stub for communicating with the Data Agent (Team 1)."""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class DataAgentClient:
    """Stub: fetches raw data from the Data Agent."""

    def __init__(self, base_url: str = "http://localhost:8000/api/v1/data"):
        self.base_url = base_url

    def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Fetch raw user data."""
        logger.warning("DataAgentClient.get_user_data() is a stub")
        return {}

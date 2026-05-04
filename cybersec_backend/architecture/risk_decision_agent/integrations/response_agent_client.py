"""Client stub for communicating with the Response Agent (Team 4)."""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ResponseAgentClient:
    """Stub: forwards decisions to the Response Agent."""

    def __init__(self, base_url: str = "http://localhost:8000/api/v1/response"):
        self.base_url = base_url

    def send_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Forward a risk decision to Team 4 for reporting/action."""
        logger.warning("ResponseAgentClient.send_decision() is a stub")
        return {"status": "stub", "received": True}

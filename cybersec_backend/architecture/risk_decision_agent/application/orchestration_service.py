"""
Orchestration Service — connects API layer to domain logic.

Manages singleton instances of LLMReasoner and DecisionAgent per process.
"""

from __future__ import annotations

import json
import logging
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..domain.decision_engine import DecisionAgent, _DEFAULT_DATA_DIR
from ..domain.reasoning import LLMConfig, LLMReasoner

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_service_instance: Optional["OrchestrationService"] = None


def get_orchestration_service() -> "OrchestrationService":
    """Return a process-global OrchestrationService singleton."""
    global _service_instance
    if _service_instance is not None:
        return _service_instance
    with _lock:
        if _service_instance is not None:
            return _service_instance
        _service_instance = OrchestrationService()
        return _service_instance


class OrchestrationService:
    """Glue between the DRF API layer and the Decision Agent domain."""

    def __init__(
        self,
        *,
        data_dir: Optional[Path] = None,
        verbose: bool = True,
    ):
        self._data_dir = data_dir or _DEFAULT_DATA_DIR

        # Initialise LLM early to fail fast.
        try:
            self._llm = LLMReasoner(LLMConfig())
        except Exception as e:
            logger.error("LLM initialization failed: %s", e)
            raise

        self._agent = DecisionAgent(
            self._llm,
            data_dir=self._data_dir,
            verbose=verbose,
        )
        logger.info("OrchestrationService initialized (data_dir=%s)", self._data_dir)

    # ── Public API ────────────────────────────────────────────────────────

    def analyze_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single anomaly event and return the decision."""
        try:
            decision = self._agent.decide(event_data)
            return {"ok": True, "decision": decision}
        except Exception as e:
            logger.exception("Error analyzing event %s", event_data.get("event_id"))
            return {
                "ok": False,
                "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc().rstrip(),
            }

    def analyze_batch(
        self,
        events: List[Dict[str, Any]],
        parallel: int = 1,
    ) -> List[Dict[str, Any]]:
        """Analyze multiple events, optionally in parallel."""
        if parallel <= 1 or len(events) <= 1:
            return [self.analyze_event(ev) for ev in events]

        results: Dict[int, Dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=min(parallel, len(events))) as ex:
            future_to_idx = {
                ex.submit(self._analyze_quiet, ev): idx
                for idx, ev in enumerate(events)
            }
            for fut in as_completed(future_to_idx):
                idx = future_to_idx[fut]
                results[idx] = fut.result()

        return [results[i] for i in range(len(events))]

    def get_cache_stats(self) -> Dict[str, Any]:
        return self._agent.get_cache_stats()

    def clear_cache(self) -> None:
        self._agent.clear_caches()

    def cleanup_cache(self) -> int:
        if self._agent.cache:
            return self._agent.cache.cleanup_expired()
        return 0

    def get_sample_events(self) -> List[Dict[str, Any]]:
        """Load sample events from local_data (useful for testing)."""
        events_path = self._data_dir / "sample_anomaly_events.json"
        try:
            with open(events_path) as f:
                raw = json.load(f)
                return raw.get("events", raw)
        except Exception:
            return []

    # ── Internals ─────────────────────────────────────────────────────────

    def _analyze_quiet(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze without verbose output (for parallel batch)."""
        try:
            # Use a thread-local agent with verbose=False for parallel runs.
            llm = LLMReasoner(LLMConfig())
            agent = DecisionAgent(llm, data_dir=self._data_dir, verbose=False)
            decision = agent.decide(event_data)
            return {"ok": True, "decision": decision}
        except Exception as e:
            return {
                "ok": False,
                "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc().rstrip(),
            }

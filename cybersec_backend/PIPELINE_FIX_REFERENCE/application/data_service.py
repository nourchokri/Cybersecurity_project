"""Data Service - orchestrates MCP servers and agent logic.

THIS IS THE CORE FILE FOR PIPELINE FUNCTIONALITY.

Key method: collect_and_forward_to_behavior() - lines 40-125
This method orchestrates the entire pipeline flow.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger('data_agent')

# Singleton instance
_service_instance = None


def get_data_service():
    """Get or create the singleton DataService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = DataService()
    return _service_instance


class DataService:
    """Orchestrates data collection, storage, and analysis."""

    def __init__(self):
        """Initialize the service with MCP client connections."""
        from ..infrastructure.mcp_integration import MCPClientManager
        from ..application.session_aggregator import SessionAggregator
        from ..integrations.behavior_agent_client import BehaviorAgentClient
        
        self.mcp_manager = MCPClientManager()
        self.session_aggregator = SessionAggregator()
        self.behavior_client = BehaviorAgentClient()
        logger.info('DataService initialized with MCP integration')

    # ================================================================
    # CRITICAL: This is the main pipeline method
    # ================================================================
    def collect_and_forward_to_behavior(self, collectors: List[str]) -> Dict[str, Any]:
        """
        Pipeline mode: Collect events and forward to Behavior Agent via A2A.

        This is called when "Start Pipeline" button is clicked.
        
        Flow:
        1. Collect events from MCP collectors
        2. Extract events from collection results
        3. Aggregate events into sessions
        4. Send sessions to Behavior Agent via HTTP
        5. Return combined results
        
        Args:
            collectors: Optional hint list of collector names

        Returns:
            {
                "ok": bool,
                "llm_reasoning": str,
                "tools_executed": [str],
                "events_by_tool": {str: int},
                "total_events": int,
                "sessions_created": int,
                "behavior_result": {
                    "ok": bool,
                    "sessions_sent": int,
                    "flagged_count": int,
                    "results": [...]
                },
                "timestamp": str,
                "status": str
            }
        """
        logger.info("Pipeline mode: Collecting events and forwarding to Behavior Agent")

        # Step 1: Collect events (same as normal collection)
        collection_result = self.collect_events(collectors)

        if not collection_result.get('ok'):
            return {
                **collection_result,
                'sessions_created': 0,
                'behavior_result': {
                    'ok': False,
                    'error': 'Collection failed',
                    'sessions_sent': 0,
                    'flagged_count': 0,
                },
            }

        # Step 2: Extract collected events from MCP tool results
        all_events = self._extract_events_from_collection(collection_result)
        
        if not all_events:
            logger.warning("No events collected, skipping Behavior Agent forwarding")
            return {
                **collection_result,
                'sessions_created': 0,
                'behavior_result': {
                    'ok': False,
                    'error': 'No events to forward',
                    'sessions_sent': 0,
                    'flagged_count': 0,
                },
            }

        # Step 3: Aggregate events into sessions
        sessions = self.session_aggregator.aggregate_events_to_sessions(all_events)
        
        if not sessions:
            logger.warning("No sessions created from events")
            return {
                **collection_result,
                'sessions_created': 0,
                'behavior_result': {
                    'ok': False,
                    'error': 'No sessions created',
                    'sessions_sent': 0,
                    'flagged_count': 0,
                },
            }

        # Step 4: Send sessions to Behavior Agent via A2A (HTTP POST)
        behavior_result = self.behavior_client.send_sessions(
            sessions,
            pipeline_mode=True
        )

        logger.info(
            f"Pipeline complete: {collection_result['total_events']} events → "
            f"{len(sessions)} sessions → Behavior Agent "
            f"({behavior_result.get('flagged_count', 0)} flagged)"
        )

        return {
            **collection_result,
            'sessions_created': len(sessions),
            'behavior_result': behavior_result,
        }

    def _extract_events_from_collection(
        self,
        collection_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract StandardEvent objects from collection result.

        CRITICAL: The collection result must include 'collected_events' key
        with the actual event dictionaries (not just counts).

        Args:
            collection_result: Result from collect_events()

        Returns:
            List of StandardEvent dictionaries
        """
        # Events are directly included in the result
        all_events = collection_result.get('collected_events', [])
        
        logger.info(f"Extracted {len(all_events)} events from collection")
        return all_events

    def collect_events(self, collectors: List[str]) -> Dict[str, Any]:
        """
        Collect events using the LLM-driven agentic approach.

        CRITICAL: This method must return 'collected_events' in the result,
        not just event counts.

        Args:
            collectors: Optional hint list of collector names

        Returns:
            {
                "ok": bool,
                "llm_reasoning": str,
                "tools_executed": [str],
                "events_by_tool": {str: int},
                "total_events": int,
                "collected_events": [dict],  # ← CRITICAL: Actual event objects
                "collectors": [str],
                "timestamp": str,
                "status": str
            }
        """
        logger.info(
            f"collect_events called — collector hint: "
            f"{collectors if collectors else '(LLM decides)'}"
        )

        try:
            # Delegate to MCP manager
            result = self.mcp_manager.run_agent_iteration(collectors=collectors)

            if not result.get('ok'):
                return {
                    'ok': False,
                    'error': result.get('error', 'Agent iteration failed'),
                    'llm_reasoning': result.get('llm_reasoning', ''),
                    'tools_executed': [],
                    'events_by_tool': {},
                    'total_events': 0,
                    'collected_events': [],  # ← Empty list on failure
                    'collectors': [],
                    'timestamp': result.get('timestamp', datetime.now().isoformat()),
                    'status': 'failed',
                }

            response: Dict[str, Any] = {
                'ok': True,
                'llm_reasoning': result.get('llm_reasoning', ''),
                'tools_executed': result.get('tools_executed', []),
                'events_by_tool': result.get('events_by_tool', {}),
                'total_events': result.get('total_events', 0),
                'collected_events': result.get('collected_events', []),  # ← CRITICAL: Pass through events
                'collectors': result.get('tools_executed', []),
                'timestamp': result.get('timestamp', datetime.now().isoformat()),
                'status': 'success',
            }

            if 'errors' in result:
                response['errors'] = result['errors']
                response['status'] = 'partial'

            logger.info(
                f"collect_events succeeded — "
                f"{response['total_events']} events from "
                f"{len(response['tools_executed'])} tool(s)"
            )
            return response

        except Exception as e:
            logger.exception('collect_events: unexpected failure')
            return {
                'ok': False,
                'error': str(e),
                'llm_reasoning': '',
                'tools_executed': [],
                'events_by_tool': {},
                'total_events': 0,
                'collected_events': [],
                'collectors': [],
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
            }

    # Other methods omitted for brevity - see full file for complete implementation

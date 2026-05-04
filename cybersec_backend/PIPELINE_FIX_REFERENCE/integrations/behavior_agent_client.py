"""
A2A Client for Behavior Agent Communication.

This module implements the Agent-to-Agent (A2A) protocol for sending
collected data from Data Agent to Behavior Agent via HTTP.

Key method: send_sessions() - sends sessions to Behavior Agent
"""

import logging
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger('data_agent')


class BehaviorAgentClient:
    """Client for communicating with Behavior Agent via A2A protocol."""

    def __init__(self, base_url: str = 'http://127.0.0.1:8000'):
        """
        Initialize the Behavior Agent client.

        Args:
            base_url: Base URL of the Behavior Agent API
        """
        self.base_url = base_url.rstrip('/')
        self.batch_endpoint = f'{self.base_url}/api/v1/behavior/batch/'
        self.timeout = 90.0  # Behavior agent can take 30-60s with LLM

    def send_sessions(
        self,
        sessions: List[Dict[str, Any]],
        pipeline_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Send sessions to Behavior Agent for analysis via HTTP POST.

        This is the CRITICAL method that forwards data to Behavior Agent.
        It makes an HTTP POST request to the Behavior Agent's batch endpoint.

        Args:
            sessions: List of SessionInput dictionaries
            pipeline_mode: If True, this is a pipeline execution (not individual test)

        Returns:
            {
                'ok': bool,
                'sessions_sent': int,
                'results': List[Dict],  # Behavior agent results
                'flagged_count': int,
                'skipped_count': int,  # Users without baselines
                'error': str  # Only present on failure
            }
        """
        if not sessions:
            logger.warning("No sessions to send to Behavior Agent")
            return {
                'ok': False,
                'error': 'No sessions to send',
                'sessions_sent': 0,
                'results': [],
                'flagged_count': 0,
                'skipped_count': 0,
            }

        logger.info(
            f"Sending {len(sessions)} session(s) to Behavior Agent "
            f"(pipeline_mode={pipeline_mode})"
        )

        try:
            # Prepare payload
            payload = {'sessions': sessions}

            # Make HTTP POST request to Behavior Agent
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.batch_endpoint, json=payload)

            # Check response status
            if response.status_code != 200:
                error_msg = f"Behavior Agent returned {response.status_code}: {response.text[:200]}"
                logger.error(error_msg)
                return {
                    'ok': False,
                    'error': error_msg,
                    'sessions_sent': len(sessions),
                    'results': [],
                    'flagged_count': 0,
                    'skipped_count': 0,
                }

            # Parse response
            data = response.json()
            results = data.get('results', [])

            # Count flagged sessions and skipped (no baseline) sessions
            flagged_count = 0
            skipped_count = 0
            
            for r in results:
                if not r.get('ok'):
                    # Check if error is due to missing baseline
                    error_msg = r.get('error', '')
                    if 'No baseline found' in error_msg:
                        skipped_count += 1
                elif r.get('anomaly_result', {}).get('flagged'):
                    flagged_count += 1

            logger.info(
                f"Behavior Agent processed {len(results)} session(s): "
                f"{flagged_count} flagged, {skipped_count} skipped (no baseline)"
            )

            return {
                'ok': True,
                'sessions_sent': len(sessions),
                'results': results,
                'flagged_count': flagged_count,
                'skipped_count': skipped_count,
            }

        except httpx.TimeoutException:
            error_msg = f"Behavior Agent request timed out after {self.timeout}s"
            logger.error(error_msg)
            return {
                'ok': False,
                'error': error_msg,
                'sessions_sent': len(sessions),
                'results': [],
                'flagged_count': 0,
                'skipped_count': 0,
            }

        except Exception as e:
            error_msg = f"Failed to send sessions to Behavior Agent: {e}"
            logger.exception(error_msg)
            return {
                'ok': False,
                'error': error_msg,
                'sessions_sent': len(sessions),
                'results': [],
                'flagged_count': 0,
                'skipped_count': 0,
            }

    def health_check(self) -> bool:
        """
        Check if Behavior Agent is reachable.

        Returns:
            True if Behavior Agent is healthy, False otherwise
        """
        try:
            health_url = f'{self.base_url}/api/v1/behavior/health/'
            with httpx.Client(timeout=5.0) as client:
                response = client.get(health_url)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Behavior Agent health check failed: {e}")
            return False

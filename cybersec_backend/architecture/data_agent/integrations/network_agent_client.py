"""
A2A Client for Network Agent Communication.
Sends network_connection events (TCP/UDP + DNS) to the Network Agent.
Mirrors behavior_agent_client.py exactly.
"""

import logging
import httpx
from typing import List, Dict, Any

logger = logging.getLogger('data_agent')


class NetworkAgentClient:

    def __init__(self, base_url: str = 'http://127.0.0.1:8000'):
        self.base_url        = base_url.rstrip('/')
        self.analyze_endpoint = f'{self.base_url}/api/v1/network/analyze/batch/'
        self.timeout         = 300.0  # Increased timeout for large datasets

    def send_network_sessions(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        For each session that has network_events, POST them to the network agent.
        sessions: the same list that goes to behavior agent — we just filter
                  for ones that have network_events populated.
        """
        # Extract only sessions that have network events
        network_payloads = []
        for session in sessions:
            net_events = session.get('network_events', [])
            if not net_events:
                continue
            network_payloads.append({
                'user_id':  session.get('user_id', 'unknown'),
                'device_id': session.get('pc', 'unknown'),
                'events':   net_events,
            })

        if not network_payloads:
            logger.info("No network events to send to Network Agent")
            return {
                'ok': True,
                'sessions_sent': 0,
                'flagged_count': 0,
                'results': [],
            }

        logger.info(f"Sending {len(network_payloads)} network session(s) to Network Agent")

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.analyze_endpoint,
                    json={'sessions': network_payloads}
                )

            if response.status_code != 200:
                error_msg = f"Network Agent returned {response.status_code}: {response.text[:200]}"
                logger.error(error_msg)
                return {'ok': False, 'error': error_msg, 'sessions_sent': len(network_payloads)}

            data         = response.json()
            results      = data.get('results', [])
            flagged      = sum(1 for r in results if r.get('flagged'))

            logger.info(f"Network Agent processed {len(results)} session(s): {flagged} flagged")
            return {
                'ok':           True,
                'sessions_sent': len(network_payloads),
                'flagged_count': flagged,
                'results':      results,
            }

        except Exception as e:
            logger.exception("Failed to send to Network Agent")
            return {'ok': False, 'error': str(e), 'sessions_sent': len(network_payloads)}

    def health_check(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.get(f'{self.base_url}/api/v1/network/health/')
            return r.status_code == 200
        except Exception as e:
            logger.warning(f"Network Agent health check failed: {e}")
            return False
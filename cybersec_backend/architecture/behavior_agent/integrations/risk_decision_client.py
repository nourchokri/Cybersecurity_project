"""Client for forwarding scored events to Team 3 (Risk Decision Agent)."""

from _future_ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger('behavior_agent')


class RiskDecisionClient:
    """Sends AnomalyResults to Team 3's Risk Decision Agent."""

    def __init__(self, base_url: str = 'http://127.0.0.1:8000/api/v1/risk-decision'):
        self.base_url = base_url.rstrip('/')

    def forward_anomaly(self, anomaly_result: Dict[str, Any]) -> Dict[str, Any]:
        """POST an AnomalyResult to Team 3's analyze endpoint."""
        try:
            import httpx

            # Detect if this is a network result or a behavior result
            is_network = 'network_anomaly_score' in anomaly_result and \
                         anomaly_result.get('source') == ['network_agent']

            payload = {
                # ── Core fields (both types) ──────────────────────────
                'event_id':        anomaly_result.get('event_id', ''),
                'user_id':         anomaly_result.get('user_id', ''),
                'timestamp':       anomaly_result.get('timestamp', ''),
                'score':           anomaly_result.get('combined_score', 0.0),
                'combined_score':  anomaly_result.get('combined_score', 0.0),
                'triggered_rules': anomaly_result.get('triggered_rules', []),
                'confidence':      anomaly_result.get('confidence', 'medium'),
                'cold_start':      anomaly_result.get('cold_start', False),
                'simulated':       anomaly_result.get('simulated', False),
                'dimension_scores': anomaly_result.get('dimension_scores', {
                    'time': 0.0, 'device': 0.0,
                    'volume': 0.0, 'sensitivity': 0.0
                }),

                # ── Behavior fields (your teammate's results) ─────────
                'if_score':        anomaly_result.get('if_score'),
                'monitor':         'B' if is_network else 'A',

                # ── Network fields (your results) ─────────────────────
                'network_anomaly_score':    anomaly_result.get('network_anomaly_score'),
                'user_anomaly_score':       anomaly_result.get('user_anomaly_score'),
                'network_attack_category':  anomaly_result.get('network_attack_category'),
                'mitre_technique':          anomaly_result.get('mitre_technique'),
                'severity':                 anomaly_result.get('severity'),
                'source':                   anomaly_result.get('source', ['behavior_agent']),
            }

            with httpx.Client(timeout=90.0) as client:
                resp = client.post(f'{self.base_url}/analyze/', json=payload)
                resp.raise_for_status()
                logger.info(
                    f"Forwarded to Team 3: user={payload['user_id']} "
                    f"score={payload['combined_score']:.3f} "
                    f"monitor={'network' if is_network else 'behavior'}"
                )
                return {'ok': True, 'decision': resp.json()}

        except Exception as e:
            logger.warning(f'RiskDecisionClient.forward_anomaly failed: {e}')
            return {'ok': False, 'error': str(e)}

"""Attacker Service - orchestrates attack generation and agent management."""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import threading

logger = logging.getLogger('attacker_agent')

# Singleton instance
_service_instance = None


def get_attacker_service():
    """Get or create the singleton AttackerService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = AttackerService()
    return _service_instance


class AttackerService:
    """Orchestrates attack generation and adversarial agent management."""

    def __init__(self):
        """Initialize the service with MCP client connections."""
        from ..infrastructure.mcp_integration import AttackerMCPManager
        from architecture.data_agent.infrastructure.mcp_integration import MCPClientManager
        
        self.attacker_mcp = AttackerMCPManager()
        self.data_agent_mcp = MCPClientManager()  # For event storage
        self.agent_thread = None
        self.agent_running = False
        self.simulating = False  # Track single-attack simulation state
        self._last_behavior_result = None  # A2A result from Behavior Agent
        
        logger.info('AttackerService initialized')

    # ------------------------------------------------------------------ #
    # Attack Pattern Management                                           #
    # ------------------------------------------------------------------ #

    def list_attack_patterns(
        self,
        category: Optional[str] = None,
        severity: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List available attack patterns with optional filtering.
        
        Args:
            category: Filter by category (optional)
            severity: Filter by severity (optional)
            
        Returns:
            Dict with patterns list and metadata
        """
        try:
            params = {}
            if category:
                params['category'] = category
            if severity:
                params['severity'] = severity
            
            result = self.attacker_mcp.call_attack_injector(
                'list_attack_patterns',
                params
            )
            
            return {
                'ok': True,
                'patterns': result.get('patterns', []),
                'count': result.get('count', 0),
                'filters': params
            }
        except Exception as e:
            logger.exception('Failed to list attack patterns')
            return {'ok': False, 'error': str(e)}

    # ------------------------------------------------------------------ #
    # Attack Injection                                                    #
    # ------------------------------------------------------------------ #

    def inject_attack(
        self,
        attack_id: str,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Inject a single attack pattern.
        
        This method:
        1. Generates attack events via attack_injector MCP
        2. Stores events via data_agent's event_storage MCP
        3. Returns result with event count
        
        Args:
            attack_id: Attack pattern ID
            user_id: User ID for simulation (optional)
            device_id: Device ID for simulation (optional)
            
        Returns:
            Dict with injection results
        """
        try:
            # Step 1: Generate attack events
            inject_params = {
                'attack_id': attack_id,
                'is_simulated': True  # Always mark as simulated
            }
            if user_id:
                inject_params['user_id'] = user_id
            if device_id:
                inject_params['device_id'] = device_id
            
            attack_result = self.attacker_mcp.call_attack_injector(
                'inject_attack',
                inject_params
            )
            
            if not attack_result.get('events'):
                return {
                    'ok': False,
                    'error': 'No events generated'
                }
            
            events = attack_result['events']
            
            # Step 2: Store events in data_agent's event storage
            storage_result = self.data_agent_mcp.call_event_storage(
                'store_events',
                {'events': events}
            )
            
            logger.info(
                f"Attack injected: {attack_id}, "
                f"generated {len(events)} events, "
                f"stored: {storage_result.get('stored', 0)}"
            )
            
            return {
                'ok': True,
                'attack_id': attack_id,
                'events_generated': len(events),
                'events_stored': storage_result.get('stored', 0),
                'attack_name': attack_result.get('attack_name'),
                'mitre_technique': attack_result.get('mitre_technique'),
                'severity': attack_result.get('severity'),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.exception(f'Attack injection failed for {attack_id}')
            return {'ok': False, 'error': str(e)}

    # ------------------------------------------------------------------ #
    # Agent Management                                                    #
    # ------------------------------------------------------------------ #

    def start_agent(
        self,
        interval_seconds: int = 60,  # Changed from 600 to 60 for testing/demo
        max_attacks: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Start the continuous adversarial agent in a background thread.
        
        Args:
            interval_seconds: Attack interval in seconds (default: 60 seconds for testing)
            max_attacks: Maximum number of attacks (optional)
            
        Returns:
            Dict with start status
        """
        if self.agent_running:
            return {
                'ok': False,
                'error': 'Agent is already running'
            }
        
        try:
            # Start agent in background thread
            self.agent_running = True
            self.agent_thread = threading.Thread(
                target=self._run_agent,
                args=(interval_seconds, max_attacks),
                daemon=True
            )
            self.agent_thread.start()
            
            logger.info(f'Adversarial agent started (interval: {interval_seconds}s)')
            
            return {
                'ok': True,
                'message': 'Adversarial agent started',
                'interval_seconds': interval_seconds,
                'max_attacks': max_attacks,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.agent_running = False
            logger.exception('Failed to start agent')
            return {'ok': False, 'error': str(e)}

    def stop_agent(self) -> Dict[str, Any]:
        """
        Stop the continuous adversarial agent.
        
        Returns:
            Dict with stop status
        """
        if not self.agent_running:
            return {
                'ok': False,
                'error': 'Agent is not running'
            }
        
        try:
            self.agent_running = False
            
            # Wait for thread to finish (with timeout)
            if self.agent_thread and self.agent_thread.is_alive():
                self.agent_thread.join(timeout=5.0)
            
            logger.info('Adversarial agent stopped')
            
            return {
                'ok': True,
                'message': 'Adversarial agent stopped',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.exception('Failed to stop agent')
            return {'ok': False, 'error': str(e)}

    def simulate_attack(self) -> Dict[str, Any]:
        """
        Run exactly ONE complete 5-phase attack cycle in a background thread.
        
        Unlike start_agent(), this does NOT loop continuously.
        It runs phases 1-5 once and then stops automatically.
        
        Returns:
            Dict with simulation status
        """
        if self.agent_running or self.simulating:
            return {
                'ok': False,
                'error': 'An attack simulation or agent is already running'
            }
        
        try:
            self.simulating = True
            self.agent_thread = threading.Thread(
                target=self._run_single_attack,
                daemon=True
            )
            self.agent_thread.start()
            
            logger.info('Single attack simulation started')
            
            return {
                'ok': True,
                'message': 'Attack simulation started (single cycle)',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.simulating = False
            logger.exception('Failed to start attack simulation')
            return {'ok': False, 'error': str(e)}

    def _run_agent(self, interval_seconds: int, max_attacks: Optional[int]):
        """
        Internal method to run the adversarial agent.
        
        Initializes and runs the LLM-powered adversarial agent in the background.
        """
        # Setup frontend logging
        from .log_manager import setup_frontend_logging
        setup_frontend_logging()
        
        logger.info(f'Starting LLM adversarial agent (interval: {interval_seconds}s, max_attacks: {max_attacks})')
        
        try:
            from ..agents.llm_adversarial_agent import LLMAdversarialAgent
            from architecture.data_agent.agents.mcp_client_factory import MCPClientFactory
            from architecture.data_agent.agents.llm_config import load_llm_config
            from pathlib import Path
            import json
            
            # Load agent configuration
            config = {
                "agents": {
                    "adversarial": {
                        "attack_interval_seconds": interval_seconds,
                        "max_attacks": max_attacks
                    }
                }
            }
            
            # Load MCP configuration for both attacker and data agent MCP servers
            # Get paths
            # __file__ is: cybersec_backend/architecture/attacker_agent/application/attacker_service.py
            attacker_root = Path(__file__).parent.parent  # architecture/attacker_agent
            backend_root = attacker_root.parent.parent  # cybersec_backend
            data_agent_root = backend_root / 'architecture' / 'data_agent'  # cybersec_backend/architecture/data_agent
            
            # Load data agent's MCP config
            data_mcp_config_path = data_agent_root / 'mcp_config.json'
            with open(data_mcp_config_path, 'r') as f:
                mcp_config = json.load(f)
            
            # Add attacker agent's MCP server to config
            mcp_config['mcp_servers']['attack_injector_attacker'] = {
                'command': 'python',
                'args': ['-m', 'architecture.attacker_agent.mcp_servers.attack_injector.server'],
                'cwd': str(backend_root),
                'transport': 'stdio',
                'description': 'Attacker agent attack pattern generation'
            }
            
            # Initialize MCP factory with config
            mcp_factory = MCPClientFactory(config=mcp_config, logger=logger)
            
            # Initialize agent
            agent = LLMAdversarialAgent(
                config=config,
                mcp_factory=mcp_factory,
                logger=logger
            )
            
            # Run agent (blocks until stopped)
            agent.run()
            
        except Exception as e:
            logger.error(f'Error running adversarial agent: {e}', exc_info=True)
            self.agent_running = False

    def _run_single_attack(self):
        """
        Internal method to run exactly ONE attack cycle.
        
        After the attack generates and stores events, it:
        1. Queries the stored events back from Data Agent's MCP storage
        2. Aggregates them into sessions (SessionAggregator maps user IDs to valid baselines)
        3. Forwards sessions to Behavior Agent via A2A (same protocol as Data Agent)
        
        Pipeline: Attacker (MCP) → Data Storage → SessionAggregator → A2A → Behavior Agent
        """
        # Setup frontend logging
        from .log_manager import setup_frontend_logging
        setup_frontend_logging()
        
        logger.info('Starting single attack simulation...')
        
        try:
            from ..agents.llm_adversarial_agent import LLMAdversarialAgent
            from architecture.data_agent.agents.mcp_client_factory import MCPClientFactory
            from architecture.data_agent.agents.llm_config import load_llm_config
            from architecture.data_agent.application.session_aggregator import SessionAggregator
            from architecture.data_agent.integrations.behavior_agent_client import BehaviorAgentClient
            from pathlib import Path
            import json
            
            # Load agent configuration
            config = {
                "agents": {
                    "adversarial": {
                        "attack_interval_seconds": 0,
                        "max_attacks": 1
                    }
                }
            }
            
            # Load MCP configuration
            attacker_root = Path(__file__).parent.parent
            backend_root = attacker_root.parent.parent
            data_agent_root = backend_root / 'architecture' / 'data_agent'
            
            data_mcp_config_path = data_agent_root / 'mcp_config.json'
            with open(data_mcp_config_path, 'r') as f:
                mcp_config = json.load(f)
            
            mcp_config['mcp_servers']['attack_injector_attacker'] = {
                'command': 'python',
                'args': ['-m', 'architecture.attacker_agent.mcp_servers.attack_injector.server'],
                'cwd': str(backend_root),
                'transport': 'stdio',
                'description': 'Attacker agent attack pattern generation'
            }
            
            mcp_factory = MCPClientFactory(config=mcp_config, logger=logger)
            
            agent = LLMAdversarialAgent(
                config=config,
                mcp_factory=mcp_factory,
                logger=logger
            )
            
            # Run SINGLE cycle (blocks until the 5 phases complete)
            result = agent.run_single_cycle()
            logger.info(f'Single attack simulation complete: {result}')
            
            # ── A2A FORWARDING: Attacker → Behavior Agent ────────────────
            # Same pattern the Data Agent uses in collect_and_forward_to_behavior()
            logger.info('Forwarding attack events to Behavior Agent via A2A...')
            
            try:
                # 1. Query the events that were just stored by the attack
                query_result = self.data_agent_mcp.call_event_storage(
                    'query_events',
                    {'page_size': 200}
                )
                all_events = query_result.get('events', [])
                
                # Filter to only simulated events from this attack
                attack_events = [
                    e for e in all_events
                    if e.get('metadata', {}).get('is_simulated') == True
                ]
                
                if not attack_events:
                    logger.warning('No simulated events found after attack — skipping A2A forwarding')
                    self._last_behavior_result = None
                    return
                
                logger.info(f'Found {len(attack_events)} simulated events to forward')
                
                # 2. Aggregate events into sessions (handles user ID mapping to valid baselines)
                aggregator = SessionAggregator()
                sessions = aggregator.aggregate_events_to_sessions(attack_events)
                
                # Mark sessions as simulated (attack-generated)
                for s in sessions:
                    s['simulated'] = True
                
                if not sessions:
                    logger.warning('SessionAggregator produced no sessions — skipping A2A forwarding')
                    self._last_behavior_result = None
                    return
                
                logger.info(f'Aggregated {len(attack_events)} events into {len(sessions)} sessions')
                
                # 3. Forward to Behavior Agent via A2A (same as Data Agent does)
                behavior_client = BehaviorAgentClient()
                behavior_result = behavior_client.send_sessions(
                    sessions,
                    pipeline_mode=True
                )
                
                self._last_behavior_result = behavior_result
                
                logger.info(
                    f'A2A forwarding complete: {behavior_result.get("sessions_sent", 0)} sessions sent, '
                    f'{behavior_result.get("flagged_count", 0)} flagged, '
                    f'{behavior_result.get("skipped_count", 0)} skipped'
                )
                
            except Exception as a2a_err:
                logger.error(f'A2A forwarding to Behavior Agent failed: {a2a_err}', exc_info=True)
                self._last_behavior_result = {'ok': False, 'error': str(a2a_err)}
            
        except Exception as e:
            logger.error(f'Error in single attack simulation: {e}', exc_info=True)
        finally:
            self.simulating = False

    # ------------------------------------------------------------------ #
    # A2A Result Retrieval                                                #
    # ------------------------------------------------------------------ #

    def get_behavior_result(self) -> Dict[str, Any]:
        """
        Get the latest A2A result from forwarding attack events to Behavior Agent.
        
        Returns:
            Dict with behavior analysis results, or None if no result available
        """
        if self._last_behavior_result is None:
            return {
                'ok': False,
                'error': 'No behavior result available. Run a simulation first.',
                'simulating': self.simulating
            }
        
        return {
            'ok': True,
            'behavior_result': self._last_behavior_result,
            'simulating': self.simulating
        }

    # ------------------------------------------------------------------ #
    # Statistics and History                                              #
    # ------------------------------------------------------------------ #

    def get_stats(self) -> Dict[str, Any]:
        """
        Get attack statistics from data_agent's storage.
        
        Returns:
            Dict with statistics
        """
        try:
            # Query events (we'll filter for simulated ones manually)
            query_result = self.data_agent_mcp.call_event_storage(
                'query_events',
                {
                    'page_size': 1000
                }
            )
            
            events = query_result.get('events', [])
            
            # Filter for simulated events only (is_simulated is in metadata)
            simulated_events = [
                event for event in events
                if event.get('metadata', {}).get('is_simulated') == True
            ]
            
            # Calculate statistics
            total_attacks = len(simulated_events)
            attack_types = {}
            severity_counts = {}
            
            for event in simulated_events:
                metadata = event.get('metadata', {})
                attack_type = metadata.get('attack_type', 'unknown')
                severity = metadata.get('severity', 'unknown')
                
                attack_types[attack_type] = attack_types.get(attack_type, 0) + 1
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            return {
                'ok': True,
                'total_attacks': total_attacks,
                'by_type': attack_types,
                'by_severity': severity_counts,
                'agent_running': self.agent_running,
                'simulating': self.simulating,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.exception('Failed to get stats')
            return {'ok': False, 'error': str(e)}

    def get_history(self, limit: int = 100) -> Dict[str, Any]:
        """
        Get recent attack history from data_agent's storage.
        
        Args:
            limit: Maximum number of attacks to return
            
        Returns:
            Dict with attack history
        """
        try:
            # Query recent events (we'll filter for simulated ones manually)
            query_result = self.data_agent_mcp.call_event_storage(
                'query_events',
                {
                    'page_size': limit * 10  # Get more events to ensure we have enough simulated ones
                }
            )
            
            events = query_result.get('events', [])
            
            # Filter for simulated events only (is_simulated is in metadata)
            simulated_events = [
                event for event in events
                if event.get('metadata', {}).get('is_simulated') == True
            ]
            
            # Group events by attack_id
            attacks = {}
            for event in simulated_events:
                metadata = event.get('metadata', {})
                attack_id = metadata.get('attack_id')
                
                if attack_id and attack_id not in attacks:
                    attacks[attack_id] = {
                        'attack_id': attack_id,
                        'attack_name': metadata.get('attack_name'),
                        'attack_type': metadata.get('attack_type'),
                        'mitre_technique': metadata.get('mitre_technique'),
                        'severity': metadata.get('severity'),
                        'timestamp': event.get('timestamp'),
                        'user_id': event.get('user_id'),
                        'device_id': event.get('device_id'),
                        'event_count': 0
                    }
                
                if attack_id:
                    attacks[attack_id]['event_count'] += 1
            
            # Sort by timestamp (most recent first) and limit
            sorted_attacks = sorted(
                attacks.values(),
                key=lambda x: x.get('timestamp', ''),
                reverse=True
            )[:limit]
            
            return {
                'ok': True,
                'attacks': sorted_attacks,
                'count': len(sorted_attacks),
                'limit': limit,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.exception('Failed to get history')
            return {'ok': False, 'error': str(e)}

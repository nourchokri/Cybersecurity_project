"""Data Service - orchestrates MCP servers and agent logic."""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from ..integrations.network_agent_client import NetworkAgentClient

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
        self.network_client = NetworkAgentClient()  
        logger.info('DataService initialized with MCP integration')

    # ------------------------------------------------------------------ #
    # Primary collection entry-points                                     #
    # ------------------------------------------------------------------ #

    def collect_and_forward_to_behavior(self, collectors: List[str]) -> Dict[str, Any]:
        """
        Pipeline mode: Collect events and forward to Behavior Agent via A2A.

        This is called when "Start Pipeline" button is clicked.
        
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

        # Step 4: Send sessions to Behavior Agent via A2A
        behavior_result = self.behavior_client.send_sessions(
            sessions,
            pipeline_mode=True
        )

        network_result = self.network_client.send_network_sessions(sessions)
        logger.info(
            f"Network Agent: {network_result.get('sessions_sent', 0)} sessions sent, "
            f"{network_result.get('flagged_count', 0)} flagged"
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

        Args:
            collection_result: Result from collect_events()

        Returns:
            List of StandardEvent dictionaries
        """
        # NEW: Events are now directly included in the result
        all_events = collection_result.get('collected_events', [])
        
        logger.info(f"Extracted {len(all_events)} events from collection")
        return all_events

    def collect_events(self, collectors: List[str]) -> Dict[str, Any]:
        """
        Collect events using the LLM-driven agentic approach.

        The LLM observes the current request, decides which of the 11
        individual MCP collector tools to run, and we return its reasoning
        alongside the collected-event counts.

        Args:
            collectors: Optional hint list of collector names.
                        Pass an empty list to let the LLM decide freely.

        Returns:
            {
                "ok":            bool,
                "llm_reasoning": str,       # what the LLM decided and why
                "tools_executed": [str],    # tools that actually ran
                "events_by_tool": {str: int},
                "total_events":  int,
                "collectors":    [str],     # alias for tools_executed
                "timestamp":     str,
                "status":        str,
                "errors":        [str]      # only present on partial failure
            }
        """
        logger.info(
            f"collect_events called — collector hint: "
            f"{collectors if collectors else '(LLM decides)'}"
        )

        try:
            # Delegate entirely to the agentic iteration.
            # The LLM reads the observation, reasons, and picks the right tools.
            result = self.mcp_manager.run_agent_iteration(collectors=collectors)

            if not result.get('ok'):
                # Propagate failure details from the iteration
                return {
                    'ok': False,
                    'error': result.get('error', 'Agent iteration failed'),
                    'llm_reasoning': result.get('llm_reasoning', ''),
                    'tools_executed': [],
                    'events_by_tool': {},
                    'total_events': 0,
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
                'collected_events': result.get('collected_events', []),  # FIXED: Pass through events
                # Keep a 'collectors' key so existing callers aren't broken
                'collectors': result.get('tools_executed', []),
                'timestamp': result.get('timestamp', datetime.now().isoformat()),
                'status': 'success',
            }

            # Surface partial-failure errors if present
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
                'collectors': [],
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
            }

    def collect_events_streaming(self, collectors: List[str]):
        """
        Generator version of collect_events with iterative batching.
        Yields progress updates in real-time as the LLM reasons through multiple iterations.
        
        Yields:
            Dict with progress updates:
            - type: 'log' for progress messages
            - type: 'complete' for final result
        """
        import time
        from ..infrastructure.mcp_integration import COLLECTOR_ONLY_TOOLS, MAX_REACT_ITERATIONS
        
        yield {'type': 'log', 'level': 'info', 'message': '🚀 Starting real data collection...'}
        time.sleep(0.1)
        
        yield {'type': 'log', 'level': 'info', 'message': '🤖 Agent observing system state...'}
        time.sleep(0.2)
        
        try:
            # Initialize agent
            agent = self.mcp_manager._get_agent()
            collector_tools = self.mcp_manager._collector_tools_for_llm(agent)
            
            # Determine target collectors
            collectors = collectors or []
            if collectors:
                target_set = {c for c in collectors if c in COLLECTOR_ONLY_TOOLS}
                if not target_set:
                    target_set = set(COLLECTOR_ONLY_TOOLS)
            else:
                target_set = set(COLLECTOR_ONLY_TOOLS)
            
            # Mutable state tracked across iterations
            collected_so_far = {}  # tool_name → event count
            pending_collectors = set(target_set)
            all_errors = []
            last_reasoning = ""
            react_iteration = 0
            
            yield {'type': 'log', 'level': 'info', 'message': f'📋 Target: {len(target_set)} collectors'}
            time.sleep(0.1)
            
            # Main ReAct loop
            while pending_collectors and react_iteration < MAX_REACT_ITERATIONS:
                react_iteration += 1
                
                yield {'type': 'log', 'level': 'info', 'message': f'🔄 Iteration {react_iteration} - {len(pending_collectors)} collectors pending'}
                time.sleep(0.2)
                
                # STEP 1: Build observation
                collected_summary = "\n".join(
                    f"  ✓ {tool:<30} → {count} events"
                    for tool, count in sorted(collected_so_far.items())
                ) if collected_so_far else "  (none yet)"
                
                pending_summary = "\n".join(
                    f"  ○ {tool}" for tool in sorted(pending_collectors)
                ) if pending_collectors else "  (all collectors have been run)"
                
                hint_line = (
                    f"The caller requested these collectors: {', '.join(collectors)}.\n"
                    if collectors
                    else "No specific collectors were requested — run ALL available collectors.\n"
                )
                
                observation = f"""ITERATIVE COLLECTION — ITERATION {react_iteration}
Time: {datetime.now().isoformat()}

{hint_line}
COLLECTION PROGRESS
-------------------
Already collected ({len(collected_so_far)} / {len(target_set)} collectors done):
{collected_summary}

Still pending ({len(pending_collectors)} remaining):
{pending_summary}

Total events collected so far: {sum(collected_so_far.values())}

AVAILABLE COLLECTOR CATEGORIES
  Lightweight : collect_system_events, collect_network_events,
                collect_process_events, collect_file_events, collect_usb_events
  Medium      : collect_registry_events, collect_dns_events
  Heavy       : collect_browser_events (hours_back required),
                collect_email_events   (hours_back required),
                collect_windows_events (hours_back required)

RULES
  • Only call collectors from the "Still pending" list above.
  • Use hours_back=1 for browser / email / windows collectors (last 1 hour only for speed).
  • Do NOT call store_events or any storage tool.
  • There are still {len(pending_collectors)} collector(s) pending. Choose ONE or MORE to run next, then stop.

YOUR TASK
  Examine the pending list. Decide which collector(s) to run next
  (you may run several in one step). Provide your reasoning and the
  tool_calls you want to execute."""
                
                # STEP 2: Clear history and reason
                agent.react_engine.llm_engine.conversation_history = []
                yield {'type': 'log', 'level': 'info', 'message': '🧠 LLM analyzing current state...'}
                
                try:
                    llm_response = agent.react_engine.llm_engine.reason(
                        system_prompt=agent.react_engine.system_prompt,
                        observation=observation,
                        available_tools=collector_tools,
                        use_native_tool_calling=agent.react_engine.use_native_tool_calling,
                    )
                except Exception as e:
                    error_msg = f"LLM reasoning failed on iteration {react_iteration}: {e}"
                    all_errors.append(error_msg)
                    yield {'type': 'log', 'level': 'error', 'message': f'❌ {error_msg}'}
                    break
                
                last_reasoning = llm_response.get('reasoning', '')
                tool_calls = llm_response.get('tool_calls', [])
                
                # Show LLM reasoning
                yield {'type': 'log', 'level': 'info', 'message': f'💭 LLM Reasoning: "{last_reasoning}"'}
                time.sleep(0.2)
                
                # Check if LLM is done
                if not tool_calls:
                    yield {'type': 'log', 'level': 'info', 'message': '✋ LLM signaled completion (no more tools)'}
                    break
                
                # Show decision
                yield {'type': 'log', 'level': 'info', 'message': f'🎯 LLM chose {len(tool_calls)} collector(s) for this iteration'}
                time.sleep(0.2)
                
                # STEP 3: Execute tools
                executed_this_step = []
                
                for tool_call in tool_calls:
                    tool_name = tool_call.get('name', '')
                    tool_args = tool_call.get('arguments', {})
                    tool_call_id = tool_call.get('id', f'call_{tool_name}_{react_iteration}')
                    
                    # Validation
                    if not tool_name:
                        continue
                    if tool_name not in COLLECTOR_ONLY_TOOLS:
                        yield {'type': 'log', 'level': 'warning', 'message': f'⚠️  Skipped non-collector: {tool_name}'}
                        continue
                    if tool_name in collected_so_far:
                        yield {'type': 'log', 'level': 'warning', 'message': f'⚠️  Already collected: {tool_name}'}
                        continue
                    
                    # Sanitize args
                    tool_args = self.mcp_manager._sanitize_args(tool_name, tool_args)
                    
                    # Show execution start
                    yield {'type': 'log', 'level': 'info', 'message': f'⚙️  Executing {tool_name}...'}
                    time.sleep(0.15)
                    
                    try:
                        result = agent.react_engine._execute_mcp_tool(tool_name, tool_args)
                        
                        # Count events
                        if isinstance(result, list):
                            event_count = len(result)
                        elif isinstance(result, dict):
                            events_field = result.get('events', result.get('data', []))
                            event_count = len(events_field) if isinstance(events_field, list) else 0
                        else:
                            event_count = 0
                        
                        # STEP 4: Update state
                        collected_so_far[tool_name] = event_count
                        pending_collectors.discard(tool_name)
                        executed_this_step.append(tool_name)
                        
                        # Show success
                        yield {'type': 'log', 'level': 'success', 'message': f'✓ {tool_name}: {event_count} events collected'}
                        time.sleep(0.15)
                        
                        # Feed compact summary back to LLM
                        compact_summary = {
                            "tool": tool_name,
                            "status": "success",
                            "events_collected": event_count,
                            "message": f"Collected {event_count} events. {len(pending_collectors)} collector(s) still pending."
                        }
                        agent.react_engine.llm_engine.add_tool_result(
                            tool_call_id=tool_call_id,
                            tool_name=tool_name,
                            result=compact_summary,
                        )
                        
                    except Exception as e:
                        error_msg = f"Tool {tool_name} failed: {e}"
                        all_errors.append(error_msg)
                        
                        # Mark as attempted
                        collected_so_far[tool_name] = 0
                        pending_collectors.discard(tool_name)
                        
                        yield {'type': 'log', 'level': 'error', 'message': f'❌ {tool_name} failed: {str(e)}'}
                        time.sleep(0.1)
                        
                        # Feed error to LLM
                        agent.react_engine.llm_engine.add_tool_result(
                            tool_call_id=tool_call_id,
                            tool_name=tool_name,
                            result={'error': str(e), 'error_type': type(e).__name__, 'message': 'Tool execution failed.'}
                        )
                
                # Check if any tools were executed
                if not executed_this_step:
                    yield {'type': 'log', 'level': 'warning', 'message': '⚠️  No valid tools executed this iteration'}
                    break
                
                # Show iteration summary
                yield {'type': 'log', 'level': 'info', 'message': f'📊 Iteration {react_iteration} complete: {len(executed_this_step)} collectors ran, {len(pending_collectors)} remaining'}
                time.sleep(0.2)
            
            # Check if max iterations reached
            if react_iteration >= MAX_REACT_ITERATIONS and pending_collectors:
                yield {'type': 'log', 'level': 'warning', 'message': f'⚠️  Reached max iterations ({MAX_REACT_ITERATIONS}) with {len(pending_collectors)} collectors still pending'}
            
            # Final summary
            total_events = sum(collected_so_far.values())
            tools_executed = list(collected_so_far.keys())
            
            yield {'type': 'log', 'level': 'success', 'message': f'✅ Collection complete: {total_events} total events from {len(tools_executed)} collectors across {react_iteration} iterations'}
            time.sleep(0.2)
            
            # Send final result
            result = {
                'ok': True,
                'llm_reasoning': last_reasoning,
                'tools_executed': tools_executed,
                'events_by_tool': collected_so_far,
                'total_events': total_events,
                'collectors': tools_executed,
                'iterations': react_iteration,
                'timestamp': datetime.now().isoformat(),
                'status': 'success',
            }
            
            if all_errors:
                result['errors'] = all_errors
                result['status'] = 'partial'
            
            yield {'type': 'complete', 'result': result}
            
        except Exception as e:
            logger.exception('Streaming collection failed')
            yield {'type': 'log', 'level': 'error', 'message': f'❌ Collection failed: {str(e)}'}
            yield {'type': 'complete', 'result': {
                'ok': False,
                'error': str(e),
                'llm_reasoning': '',
                'tools_executed': [],
                'events_by_tool': {},
                'total_events': 0,
                'collectors': [],
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
            }}

    # ------------------------------------------------------------------ #
    # Other service methods (unchanged)                                   #
    # ------------------------------------------------------------------ #

    def query_events(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Query stored events with filters.

        Args:
            filters: Query filters (start_date, end_date, event_type, user_id, limit)

        Returns:
            Dict with events and metadata
        """
        try:
            result = self.mcp_manager.call_event_storage('query_events', filters)
            return {
                'ok': True,
                'events': result.get('events', []),
                'count': result.get('count', 0),
                'filters': filters,
            }
        except Exception as e:
            logger.exception('query_events failed')
            return {'ok': False, 'error': str(e)}

    def analyze_events(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze events using LLM agent.

        Args:
            params: Analysis parameters (query, filters, max_events)

        Returns:
            Dict with analysis results
        """
        try:
            query_filters = {
                'start_date': params.get('start_date'),
                'end_date': params.get('end_date'),
                'event_type': params.get('event_type'),
                'limit': params.get('max_events', 100),
            }

            events_result = self.query_events(query_filters)
            if not events_result.get('ok'):
                return events_result

            analysis_result = self.mcp_manager.call_llm_agent(
                'analyze_events',
                {
                    'query': params['query'],
                    'events': events_result['events'],
                },
            )

            return {
                'ok': True,
                'query': params['query'],
                'events_analyzed': len(events_result['events']),
                'analysis': analysis_result.get('analysis', ''),
                'threats_detected': analysis_result.get('threats', []),
                'recommendations': analysis_result.get('recommendations', []),
            }
        except Exception as e:
            logger.exception('analyze_events failed')
            return {'ok': False, 'error': str(e)}

    def inject_attack(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Inject synthetic attack patterns.

        Args:
            params: Injection parameters (attack_type, count)

        Returns:
            Dict with injection results
        """
        try:
            result = self.mcp_manager.call_attack_injector('inject_attack', params)
            return {
                'ok': True,
                'injected': result.get('events_injected', 0),
                'attack_type': result.get('attack_type'),
                'patterns': result.get('patterns', []),
            }
        except Exception as e:
            logger.exception('inject_attack failed')
            return {'ok': False, 'error': str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about collected events.

        Returns:
            Dict with statistics
        """
        try:
            result = self.mcp_manager.call_event_storage('get_statistics', {})
            return {
                'ok': True,
                'total_events': result.get('total_events', 0),
                'by_type': result.get('by_type', {}),
                'by_date': result.get('by_date', {}),
                'storage_size': result.get('storage_size', 0),
            }
        except Exception as e:
            logger.exception('get_stats failed')
            return {'ok': False, 'error': str(e)}
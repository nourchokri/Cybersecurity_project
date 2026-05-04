"""Direct integration with existing LLM Data Engineering Agent."""
import logging
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

logger = logging.getLogger('data_agent')

# Global agent instance (lazy initialization)
_agent_instance = None

# ---------------------------------------------------------------------------
# All collector tools the LLM may choose from during iteration.
#
# collect_clipboard_events is excluded because its MCP implementation runs a
# blocking 60-second monitor, which always causes a request timeout.
# ---------------------------------------------------------------------------
COLLECTOR_ONLY_TOOLS: Set[str] = {
    "collect_system_events",
    "collect_network_events",
    "collect_process_events",
    "collect_file_events",
    "collect_usb_events",
    "collect_registry_events",
    "collect_dns_events",
    "collect_browser_events",
    "collect_email_events",
    "collect_windows_events",
    # collect_clipboard_events intentionally omitted (blocks for 60 s)
}

# ---------------------------------------------------------------------------
# Strip known-unsupported arguments before forwarding to MCP so we never get
# "unexpected keyword argument" errors from specific server implementations.
# ---------------------------------------------------------------------------
STRIP_ARGS: Dict[str, List[str]] = {
    # The DNS collector reads from the live Windows DNS cache; the MCP server
    # wrapper does not forward hours_back to collect_dns_queries().
    "collect_dns_events": ["hours_back"],
}

# Maximum ReAct iterations before we force-stop to prevent infinite loops.
MAX_REACT_ITERATIONS = 20


class MCPClientManager:
    """Simple wrapper around the existing agent with lazy initialization."""

    def __init__(self):
        """Initialize paths only, defer agent creation."""
        self.data_agent_root = Path(__file__).resolve().parent.parent
        if str(self.data_agent_root) not in sys.path:
            sys.path.insert(0, str(self.data_agent_root))
        self.agent = None

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _get_agent(self):
        """Lazy initialization of agent (called on first use)."""
        global _agent_instance

        if _agent_instance is None:
            try:
                from agents.llm_data_engineering_agent import LLMDataEngineeringAgent
                from agents.mcp_client_factory import MCPClientFactory

                config_path = self.data_agent_root / 'agents' / 'config.json'
                with open(config_path, 'r') as f:
                    config = json.load(f)

                mcp_config_path = self.data_agent_root / 'mcp_config.json'
                with open(mcp_config_path, 'r') as f:
                    mcp_config = json.load(f)

                mcp_factory = MCPClientFactory(mcp_config, logger)
                _agent_instance = LLMDataEngineeringAgent(config, mcp_factory)
                logger.info('Data Engineering Agent initialized successfully')
            except Exception as e:
                logger.error(f'Failed to initialize agent: {e}')
                raise

        return _agent_instance

    def _collector_tools_for_llm(self, agent) -> List[Dict[str, Any]]:
        """
        Return only the collector-tool definitions from the agent's full
        available_tools list.
        """
        return [
            t for t in agent.react_engine.available_tools
            if t.get("function", {}).get("name") in COLLECTOR_ONLY_TOOLS
        ]

    def _sanitize_args(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Strip known-unsupported arguments before forwarding to MCP.
        Returns a new dict; the original is never mutated.
        """
        to_strip = STRIP_ARGS.get(tool_name)
        if not to_strip:
            return args
        cleaned = {k: v for k, v in args.items() if k not in to_strip}
        if cleaned != args:
            stripped = set(args) - set(cleaned)
            logger.debug(f"Stripped unsupported arg(s) {stripped} from {tool_name} call")
        return cleaned

    def _build_observation(
        self,
        collected_so_far: Dict[str, int],
        pending_collectors: Set[str],
        iteration: int,
        requested_collectors: List[str],
    ) -> str:
        """
        Build a rich, state-aware observation for the LLM so it can reason
        about what has already been collected and what still needs to run.

        Args:
            collected_so_far:     {tool_name: event_count} for completed tools
            pending_collectors:   set of tool names not yet executed
            iteration:            current ReAct iteration number (1-based)
            requested_collectors: optional caller-supplied hint list
        """
        collected_summary = (
            "\n".join(
                f"  ✓ {tool:<30} → {count} events"
                for tool, count in sorted(collected_so_far.items())
            )
            if collected_so_far
            else "  (none yet)"
        )

        pending_summary = (
            "\n".join(f"  ○ {tool}" for tool in sorted(pending_collectors))
            if pending_collectors
            else "  (all collectors have been run)"
        )

        hint_line = (
            f"The caller requested these collectors: {', '.join(requested_collectors)}.\n"
            if requested_collectors
            else "No specific collectors were requested — run ALL available collectors.\n"
        )

        done_signal = (
            "ALL collectors have been executed. "
            "Respond with an EMPTY tool_calls list to signal completion."
            if not pending_collectors
            else (
                f"There are still {len(pending_collectors)} collector(s) pending. "
                "Choose ONE or MORE to run next, then stop."
            )
        )

        return f"""ITERATIVE COLLECTION — ITERATION {iteration}
Time: {datetime.now().isoformat()}

{hint_line}
COLLECTION PROGRESS
-------------------
Already collected ({len(collected_so_far)} / {len(COLLECTOR_ONLY_TOOLS)} collectors done):
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
  • {done_signal}

YOUR TASK
  Examine the pending list. Decide which collector(s) to run next
  (you may run several in one step). Provide your reasoning and the
  tool_calls you want to execute.
"""

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def run_agent_iteration(
        self,
        collectors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run a full iterative ReAct collection loop.

        The agent observes its own progress after every tool execution,
        decides which collector to run next, and keeps going until it has
        run every collector (or signals completion itself).

        Each ReAct step:
          1. OBSERVE  – show the LLM what has been collected and what is pending
          2. REASON   – LLM picks the next collector(s) to run
          3. ACT      – execute those collectors via MCP
          4. UPDATE   – append results to collected_so_far, remove from pending
          5. REPEAT   – until pending is empty or LLM returns no tool_calls

        Args:
            collectors: Optional hint list of collectors the caller wants.
                        Pass [] or None to let the LLM decide which to run.

        Returns:
            {
                "ok":             bool,
                "llm_reasoning":  str   (last LLM reasoning block),
                "tools_executed": [str, ...],
                "events_by_tool": {tool_name: event_count, ...},
                "total_events":   int,
                "iterations":     int,
                "timestamp":      str,
                "errors":         [str, ...]   # only on partial/full failure
            }
        """
        collectors = collectors or []
        logger.info(
            "Starting iterative agent collection "
            f"(hint={collectors if collectors else 'LLM decides'})"
        )

        # ------------------------------------------------------------------
        # 0. Initialise agent
        # ------------------------------------------------------------------
        try:
            agent = self._get_agent()
        except Exception as e:
            return {
                'ok': False,
                'error': f'Agent initialisation failed: {e}',
                'llm_reasoning': '',
                'tools_executed': [],
                'events_by_tool': {},
                'total_events': 0,
                'iterations': 0,
                'timestamp': datetime.now().isoformat(),
            }

        collector_tools = self._collector_tools_for_llm(agent)

        # Determine the universe of collectors we want to run.
        # If the caller supplied a hint list, restrict to that subset;
        # otherwise use the full COLLECTOR_ONLY_TOOLS set.
        if collectors:
            target_set: Set[str] = {
                c for c in collectors if c in COLLECTOR_ONLY_TOOLS
            }
            if not target_set:
                logger.warning(
                    "Requested collectors not in COLLECTOR_ONLY_TOOLS — "
                    "falling back to full set"
                )
                target_set = set(COLLECTOR_ONLY_TOOLS)
        else:
            target_set = set(COLLECTOR_ONLY_TOOLS)

        # Mutable state tracked across iterations
        collected_so_far: Dict[str, int] = {}   # tool_name → event count
        pending_collectors: Set[str] = set(target_set)
        all_errors: List[str] = []
        last_reasoning: str = ""
        react_iteration = 0
        all_collected_events: List[Dict[str, Any]] = []  # NEW: Accumulate actual events

        # ------------------------------------------------------------------
        # Main ReAct loop
        # ------------------------------------------------------------------
        while pending_collectors and react_iteration < MAX_REACT_ITERATIONS:
            react_iteration += 1
            logger.info(
                f"=== ReAct Iteration {react_iteration} | "
                f"Pending: {len(pending_collectors)} collectors ==="
            )

            # ---- STEP 1: OBSERVE ----------------------------------------
            observation = self._build_observation(
                collected_so_far=collected_so_far,
                pending_collectors=pending_collectors,
                iteration=react_iteration,
                requested_collectors=collectors,
            )
            logger.debug(f"Observation built ({len(observation)} chars)")

            # ---- STEP 2: REASON -----------------------------------------
            # Clear conversation history before EVERY reason() call.
            # The observation already encodes the full collection state
            # (what ran, what's pending, event counts), so prior messages
            # add zero value but thousands of tokens.  Keeping them caused
            # the 136k-token context-window overflow on iteration 2+.
            agent.react_engine.llm_engine.conversation_history = []
            logger.debug(
                f"Cleared LLM conversation history before iteration {react_iteration}"
            )

            try:
                llm_response = agent.react_engine.llm_engine.reason(
                    system_prompt=agent.react_engine.system_prompt,
                    observation=observation,
                    available_tools=collector_tools,
                    use_native_tool_calling=agent.react_engine.use_native_tool_calling,
                )
            except Exception as e:
                err = f"LLM reasoning failed on iteration {react_iteration}: {e}"
                logger.error(err, exc_info=True)
                all_errors.append(err)
                break  # Cannot continue without LLM guidance

            last_reasoning = llm_response.get('reasoning', '')
            tool_calls = llm_response.get('tool_calls', [])

            logger.info(f"LLM reasoning: {last_reasoning[:300]}…")
            logger.info(
                f"LLM chose {len(tool_calls)} tool(s): "
                f"{[tc.get('name') for tc in tool_calls]}"
            )

            # LLM returned no tool calls → it signals it is done
            if not tool_calls:
                logger.info(
                    "LLM returned no tool calls — treating as completion signal"
                )
                break

            # ---- STEP 3: ACT --------------------------------------------
            executed_this_step: List[str] = []

            for tool_call in tool_calls:
                tool_name = tool_call.get('name', '')
                tool_args = tool_call.get('arguments', {})
                tool_call_id = tool_call.get('id', f'call_{tool_name}_{react_iteration}')

                if not tool_name:
                    logger.warning("Skipping tool call with empty name")
                    continue

                # Safety guard — reject non-collector tools
                if tool_name not in COLLECTOR_ONLY_TOOLS:
                    logger.warning(
                        f"LLM tried to call non-collector '{tool_name}' — skipped"
                    )
                    continue

                # Reject tools that have already been collected
                if tool_name in collected_so_far:
                    logger.warning(
                        f"LLM re-requested already-collected tool '{tool_name}' — skipped"
                    )
                    continue

                # Strip unsupported args
                tool_args = self._sanitize_args(tool_name, tool_args)

                logger.info(f"  → Executing: {tool_name}  args={tool_args}")
                try:
                    result = agent.react_engine._execute_mcp_tool(tool_name, tool_args)

                    # Count events in the result AND extract them
                    events_list = []
                    if isinstance(result, list):
                        event_count = len(result)
                        events_list = result
                    elif isinstance(result, dict):
                        events_field = result.get('events', result.get('data', []))
                        event_count = len(events_field) if isinstance(events_field, list) else 0
                        events_list = events_field if isinstance(events_field, list) else []
                    else:
                        event_count = 0
                    
                    # NEW: Accumulate actual events for pipeline mode
                    if events_list:
                        all_collected_events.extend(events_list)

                    # ---- STEP 4: UPDATE STATE ---------------------------
                    collected_so_far[tool_name] = event_count
                    pending_collectors.discard(tool_name)
                    executed_this_step.append(tool_name)

                    logger.info(f"     {tool_name}: {event_count} events collected")
                    logger.info(
                        f"     Progress: {len(collected_so_far)}/{len(target_set)} done, "
                        f"{len(pending_collectors)} pending"
                    )

                    # Feed ONLY a compact summary back to the LLM — never the
                    # raw event list.  A single network-events payload can be
                    # 50k+ tokens; feeding it back caused the 136k context-
                    # window overflow that crashed iteration 2.
                    compact_summary = {
                        "tool": tool_name,
                        "status": "success",
                        "events_collected": event_count,
                        "message": (
                            f"Collected {event_count} events. "
                            f"{len(pending_collectors)} collector(s) still pending."
                        ),
                    }
                    agent.react_engine.llm_engine.add_tool_result(
                        tool_call_id=tool_call_id,
                        tool_name=tool_name,
                        result=compact_summary,
                    )

                except Exception as e:
                    err_msg = f"Tool {tool_name} failed: {e}"
                    logger.error(err_msg, exc_info=True)
                    all_errors.append(err_msg)

                    # Still mark as attempted so the LLM does not retry it
                    collected_so_far[tool_name] = 0
                    pending_collectors.discard(tool_name)
                    executed_this_step.append(tool_name)  # FIXED: Add to executed list so loop continues

                    # Feed error back to LLM
                    agent.react_engine.llm_engine.add_tool_result(
                        tool_call_id=tool_call_id,
                        tool_name=tool_name,
                        result={
                            'error': str(e),
                            'error_type': type(e).__name__,
                            'message': 'Tool execution failed.',
                        },
                    )

            # If the LLM chose only invalid/already-done tools, break to
            # avoid an infinite loop of no-ops.
            if not executed_this_step:
                logger.warning(
                    "No tools were executed this iteration despite LLM tool_calls — "
                    "breaking to avoid infinite loop"
                )
                break

        # ------------------------------------------------------------------
        # 5. Compile final result
        # ------------------------------------------------------------------
        if react_iteration >= MAX_REACT_ITERATIONS and pending_collectors:
            logger.warning(
                f"Reached MAX_REACT_ITERATIONS ({MAX_REACT_ITERATIONS}) with "
                f"{len(pending_collectors)} collectors still pending: {pending_collectors}"
            )

        total_events = sum(collected_so_far.values())
        tools_executed = list(collected_so_far.keys())

        logger.info(
            f"Iterative collection complete — {react_iteration} iteration(s), "
            f"{len(tools_executed)} collectors ran, {total_events} total events"
        )

        payload: Dict[str, Any] = {
            'ok': True,
            'llm_reasoning': last_reasoning,
            'tools_executed': tools_executed,
            'events_by_tool': collected_so_far,
            'total_events': total_events,
            'iterations': react_iteration,
            'timestamp': datetime.now().isoformat(),
            'collected_events': all_collected_events,  # NEW: Include actual events
        }
        if all_errors:
            payload['errors'] = all_errors
            if not tools_executed:
                payload['ok'] = False

        return payload

    # ------------------------------------------------------------------ #
    # Legacy / other MCP calls (kept for backward-compatibility)          #
    # ------------------------------------------------------------------ #

    def call_collector_executor(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a single named collector tool directly (bypasses LLM)."""
        agent = self._get_agent()
        return agent.execute_mcp_tool('collector_executor', tool_name, params)

    def call_event_storage(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call storage via agent."""
        agent = self._get_agent()
        return agent.execute_mcp_tool('event_storage', tool_name, params)

    def call_attack_injector(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call injector via agent."""
        agent = self._get_agent()
        return agent.execute_mcp_tool('attack_injector', tool_name, params)

    def call_llm_agent(self, task: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call LLM agent directly."""
        agent = self._get_agent()
        return agent.execute_task(task, params)
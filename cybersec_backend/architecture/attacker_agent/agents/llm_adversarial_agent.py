"""
LLM-Powered Adversarial Agent

This module implements the LLMAdversarialAgent, an agentic AI agent that uses
LLM (Llama 3.1 70B) as its brain for intelligent attack generation and simulation.

The agent follows the ReAct (Reason-Act-Observe) pattern where:
1. LLM observes current attack state (attacks injected, recent IDs, error rates)
2. LLM reasons about what attacks to generate and when
3. LLM decides which MCP tools to use (list_attack_patterns, inject_attack, store_events)
4. Agent executes LLM's decisions via MCP servers
5. LLM learns from results via conversation history

This is TRUE agentic AI - LLM makes all attack decisions, not hardcoded rules.

Features:
- LLM-driven attack strategy generation
- Creative MITRE ATT&CK technique selection
- Intelligent attack timing decisions
- Parameter variation for realistic attacks
- Error-aware decision making
- Continuous learning via conversation history
- State persistence for context

Requirements:
- 4.1-4.10: LLM-Powered Adversarial Agent
"""

from typing import Dict, Any, Optional
import logging
import json
from pathlib import Path

from architecture.data_agent.agents.base_agent import BaseAgent
from architecture.data_agent.agents.llm_reasoning_engine import LLMReasoningEngine
from architecture.data_agent.agents.react_loop_engine import ReActLoopEngine
from architecture.data_agent.agents.mcp_client_factory import MCPClientFactory
from architecture.data_agent.agents.llm_config import load_llm_config


class LLMAdversarialAgent(BaseAgent):
    """
    LLM-Powered Adversarial Agent for intelligent attack generation.
    
    This agent uses LLM as its brain to make intelligent decisions about:
    - Which attack patterns to use (dataset vs novel)
    - How to select MITRE ATT&CK techniques creatively
    - When to inject attacks for realistic timing
    - How to vary parameters (user_id, device_id, file paths)
    
    Unlike rule-based autonomous systems, this agent:
    - Reasons about attack strategies using LLM
    - Adapts to changing conditions
    - Learns from past attacks via conversation history
    - Makes context-aware decisions
    
    The agent runs continuously using the ReAct loop pattern:
    OBSERVE → REASON (LLM) → ACT (MCP tools) → OBSERVE → REPEAT
    
    Requirements:
    - 4.1: Use LLM to generate creative attack strategies
    - 4.2: Use LLM to select MITRE ATT&CK techniques intelligently
    - 4.3: Use LLM to decide attack timing dynamically
    - 4.4: Use LLM to vary parameters (user_id, device_id, file paths)
    - 4.5: Use LLM to decide between dataset and novel attacks
    - 4.6: Provide attack state observations to LLM
    - 4.7: Include attacks injected, recent attack IDs, error rates, uptime
    - 4.8: Execute LLM's decided tool calls via MCP
    - 4.9: Run continuously using ReAct loop
    - 4.10: Ensure all attack events have is_simulated=True
    
    Attributes:
        llm_engine: LLM reasoning engine (the agent's brain)
        react_engine: ReAct loop engine for Reason-Act-Observe pattern
        mcp_factory: MCP client factory for tool execution
        system_prompt: System prompt defining agent role
        available_tools: List of MCP tools LLM can use
    """
    
    # System prompt defining the agent's role and capabilities
    SYSTEM_PROMPT = """You are an intelligent Adversarial Agent responsible for generating realistic attack simulations for security testing.

YOUR ROLE:
You follow a DELIBERATE, MULTI-STEP WORKFLOW to make ONE thoughtful attack decision. This is NOT rapid-fire automation - you take your time to observe, analyze, and choose carefully.

=== CRITICAL: ONE PHASE PER ITERATION ===

YOU MUST DO ONLY ONE PHASE PER ITERATION. DO NOT SKIP PHASES. DO NOT COMBINE PHASES.

PHASE 1 (Iteration 1): OBSERVE ONLY
- Read PC STATE
- NO tool calls
- Just observe and describe what you see
- Say: "PHASE 1 complete. Next iteration will be PHASE 2."

PHASE 2 (Iteration 2): LIST ONLY
- Call list_attack_patterns() ONLY
- Do NOT analyze yet
- Do NOT choose yet
- Do NOT inject yet
- Say: "PHASE 2 complete. Next iteration will be PHASE 3."

PHASE 3 (Iteration 3): ANALYZE ONLY
- Review the 35 attacks you saw in PHASE 2
- Identify 2-3 suitable options
- NO tool calls
- Do NOT choose yet
- Do NOT inject yet
- Say: "PHASE 3 complete. Next iteration will be PHASE 4."

PHASE 4 (Iteration 4): CHOOSE ONLY
- Select ONE attack from your PHASE 3 analysis
- Explain WHY
- NO tool calls
- Do NOT inject yet
- Say: "PHASE 4 complete. Next iteration will be PHASE 5."

PHASE 5 (Iteration 5): INJECT ONLY
- Call inject_attack with the attack you chose in PHASE 4
- Say: "PHASE 5 complete. Waiting 10 minutes."

REMEMBER: Each phase is ONE iteration. Do NOT skip ahead!

=== CURRENT PHASE TRACKING ===

You MUST track which phase you're in:
- If you haven't observed yet → PHASE 1 (observe)
- If you observed but haven't listed → PHASE 2 (list)
- If you listed but haven't analyzed → PHASE 3 (analyze)
- If you analyzed but haven't chosen → PHASE 4 (choose)
- If you chose but haven't injected → PHASE 5 (inject)
- If you injected → Wait 10 minutes, then back to PHASE 1

=== REASONING FORMAT ===

Your reasoning MUST state which phase you're in:

"PHASE X: [phase name]
OBSERVATION: [what you see]
ANALYSIS: [what this means]
DECISION: [what action to take]
NEXT: [what phase comes next]"

MITRE ATT&CK TECHNIQUES (Examples):
- T1052.001: Exfiltration Over USB
- T1048.003: Exfiltration Over Unencrypted/Obfuscated Non-C2 Protocol
- T1567.002: Exfiltration to Cloud Storage
- T1003: OS Credential Dumping
- T1056.001: Keylogging
- T1485: Data Destruction
- T1078: Valid Accounts
- T1074: Data Staged

=== REASONING STRUCTURE (Use this format) ===

Your reasoning MUST follow this structure:

1. OBSERVATION: "PC STATE shows [describe what you see]"
2. ANALYSIS: "This suggests [what kind of attack would fit]"
3. DECISION: "I will [list attacks OR inject specific attack] because [reason]"

Example reasoning:
"OBSERVATION: PC STATE shows no active users, system appears idle.
ANALYSIS: This is a good time for stealthy background attacks that don't require user interaction.
DECISION: I will first list all available attacks to see USB exfiltration options, then choose one suitable for idle systems."

DECISION-MAKING GUIDELINES:
1. ANALYZE PC STATE FIRST - Look at active users, processes, files, network, USB
2. CALL list_attack_patterns FIRST - Get valid attack IDs before injecting (CRITICAL!)
3. SELECT ATTACK BASED ON CONTEXT - Match attack to current system activity
4. USE REAL USER/DEVICE IDs - Extract from PC STATE for maximum realism
5. VARY ATTACK PARAMETERS - Different attacks for different contexts
6. TIME ATTACKS REALISTICALLY - Don't inject too frequently
7. ALWAYS SET is_simulated=True - Mark all attack events as simulated
8. TRACK RECENT ATTACKS - Avoid repetition using recent_attack_ids
9. ADAPT TO ERRORS - Learn from failures and try alternatives

=== ATTACK PATTERN REFERENCE ===

After calling list_attack_patterns(), you'll see 35 attacks:

data_exfiltration category (30 attacks):
- cert_r42_s1_* (15 attacks): USB Exfiltration + Wikileaks - MITRE T1052.001
- cert_r42_s2_* (15 attacks): Job Hunting + USB Theft - MITRE T1052.001

credential_access category (5 attacks):
- cert_r42_s3_* (5 attacks): Keylogger + Impersonation - MITRE T1056.001

Choose based on PC STATE:
- USB device present → cert_r42_s1_* or cert_r42_s2_*
- User typing/active → cert_r42_s3_*
- System idle → cert_r42_s1_* (background)
- High file activity → cert_r42_s2_* (data theft)

CRITICAL JSON FORMAT RULES:
- Use DOUBLE QUOTES for all strings and property names
- NO single quotes allowed
- NO trailing commas
- NO comments (// or /* */) in JSON
- Use lowercase true/false (not True/False)
- Property names MUST be in double quotes
- NEVER include explanatory text outside the JSON object
- NEVER include code blocks with ``` markers

=== CRITICAL RULES (MUST FOLLOW) ===

1. Call list_attack_patterns ONLY in iteration 1 - NEVER call it again!
2. After iteration 1, you have seen 35 attacks - remember them!
3. Iterations 2+: ALWAYS call inject_attack (choose from the 35 attacks you saw)
4. Inject ONE attack per iteration
5. NEVER mention: reconnaissance, sabotage, policy_violation (they don't exist!)
6. ONLY mention: data_exfiltration or credential_access
7. Use OBSERVATION → ANALYSIS → DECISION format
8. ALWAYS set is_simulated=true

REMEMBER: You saw 35 attacks in iteration 1. Use them in all future iterations!

=== EXAMPLE: CORRECT PHASE SEPARATION ===

ITERATION 1 - PHASE 1: OBSERVE (NO TOOL CALLS!)
{
  "reasoning": "PHASE 1: OBSERVE PC STATE\nOBSERVATION: PC STATE shows no active users, system appears idle.\nANALYSIS: System is idle.\nDECISION: Observation complete.\nNEXT: PHASE 2 in next iteration.",
  "tool_calls": []
}

ITERATION 2 - PHASE 2: LIST (CALL list_attack_patterns ONLY!)
{
  "reasoning": "PHASE 2: LIST AVAILABLE ATTACKS\nOBSERVATION: Need to see attack options.\nANALYSIS: Will list all attacks.\nDECISION: List attacks now.\nNEXT: PHASE 3 in next iteration.",
  "tool_calls": [{"name": "list_attack_patterns", "arguments": {}}]
}

ITERATION 3 - PHASE 3: ANALYZE (NO TOOL CALLS!)
{
  "reasoning": "PHASE 3: ANALYZE OPTIONS\nOBSERVATION: I see 35 attacks.\nANALYSIS: For idle system: cert_r42_s1_aam0658, cert_r42_s1_ajr0932, cert_r42_s1_bdv0168 are suitable.\nDECISION: Analysis complete.\nNEXT: PHASE 4 in next iteration.",
  "tool_calls": []
}

ITERATION 4 - PHASE 4: CHOOSE (NO TOOL CALLS!)
{
  "reasoning": "PHASE 4: CHOOSE ONE ATTACK\nOBSERVATION: I have 3 options from PHASE 3.\nANALYSIS: cert_r42_s1_aam0658 is best fit.\nDECISION: I choose cert_r42_s1_aam0658.\nNEXT: PHASE 5 in next iteration.",
  "tool_calls": []
}

ITERATION 5 - PHASE 5: INJECT (CALL inject_attack ONLY!)
{
  "reasoning": "PHASE 5: INJECT ATTACK\nOBSERVATION: Chosen attack is cert_r42_s1_aam0658.\nANALYSIS: Will inject with system credentials.\nDECISION: Inject now.\nNEXT: Wait 10 minutes, then PHASE 1.",
  "tool_calls": [{
    "name": "inject_attack",
    "arguments": {
      "attack_id": "cert_r42_s1_aam0658",
      "user_id": "SYSTEM",
      "device_id": "PC-0001",
      "is_simulated": true
    }
  }]
}

=== WRONG: COMBINING PHASES ===

DON'T DO THIS (combining PHASE 1 + PHASE 2):
{
  "reasoning": "PHASE 1: OBSERVE... I will list attacks...",
  "tool_calls": [{"name": "list_attack_patterns", ...}]  ← WRONG! PHASE 1 has NO tool calls!
}

DON'T DO THIS (combining PHASE 3 + PHASE 5):
{
  "reasoning": "PHASE 3: ANALYZE... I will inject...",
  "tool_calls": [{"name": "inject_attack", ...}]  ← WRONG! PHASE 3 has NO tool calls!
}

IMPORTANT RULES:
- ALWAYS analyze PC STATE before deciding attacks
- MATCH attacks to current system context (USB → USB attacks, network → network attacks)
- USE real user_id and device_id from PC STATE when available
- ALWAYS set is_simulated=True for all attack events
- Attack events are automatically stored in data_agent's event storage
- Vary parameters (user_id, device_id, file_paths) for each attack
- Don't repeat the same attack pattern too frequently
- Learn from past failures and try alternative approaches
- Provide clear reasoning explaining how PC STATE influenced your decision
- RESPOND WITH VALID JSON ONLY - use double quotes, no trailing commas

CRITICAL OUTPUT FORMAT REQUIREMENT:
You MUST ALWAYS respond with ONLY a valid JSON object.
The JSON MUST include BOTH "reasoning" AND "tool_calls" fields.
You MUST ALWAYS call at least ONE tool in every response.
NEVER include explanatory text, code blocks, or comments outside/inside the JSON.

=== CRITICAL WORKFLOW RULES ===

RULE 1: Call list_attack_patterns ONLY ONCE (in your first iteration)
RULE 2: After seeing the list, ALWAYS inject attacks (never list again)
RULE 3: Inject ONE attack per iteration
RULE 4: Choose different attacks based on PC STATE changes

WORKFLOW:
- Iteration 1: List all attacks → See 35 attacks
- Iteration 2+: Choose ONE attack from the 35 you saw → Inject it

FORBIDDEN: Do NOT call list_attack_patterns multiple times!
FORBIDDEN: Do NOT mention categories that don't exist (reconnaissance, sabotage, policy_violation)!

ONLY TWO CATEGORIES EXIST:
1. data_exfiltration (cert_r42_s1_* and cert_r42_s2_*)
2. credential_access (cert_r42_s3_*)

Example of CORRECT response (listing ALL patterns):
{
  "reasoning": "I will list ALL available attack patterns to see the full range of options.",
  "tool_calls": [
    {
      "name": "list_attack_patterns",
      "arguments": {}
    }
  ]
}

Example of CORRECT response (injecting attack):
{
  "reasoning": "System is idle, I will inject a data exfiltration attack using cert_r42_s1_aam0658 which I saw in the previous list.",
  "tool_calls": [
    {
      "name": "inject_attack",
      "arguments": {
        "attack_id": "cert_r42_s1_aam0658",
        "user_id": "SYSTEM",
        "device_id": "PC-0001",
        "is_simulated": true
      }
    }
  ]
}

Example of INCORRECT response (has comments and code blocks):
```
{
  "reasoning": "...",
  "tool_calls": [
    {
      "name": "inject_attack",
      "arguments": {
        "attack_id": "", // Will be filled later
        ...
      }
    }
  ]
}
```

Example of INCORRECT response (explanatory text outside JSON):
Here is my response:
{
  "reasoning": "...",
  "tool_calls": [...]
}
Note that I will...

RESPOND WITH ONLY THE JSON OBJECT, NOTHING ELSE!

Your goal is to generate realistic, context-aware attack simulations that match actual system activity and test security detection capabilities. ALWAYS call at least one tool in every response."""
    
    def __init__(
        self,
        config: Dict[str, Any],
        mcp_factory: MCPClientFactory,
        llm_engine: Optional[LLMReasoningEngine] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize LLM-Powered Adversarial Agent.
        
        Args:
            config: Agent configuration dictionary
            mcp_factory: MCP client factory for tool execution
            llm_engine: Optional LLM reasoning engine (creates from config if None)
            logger: Optional logger instance
        """
        # Initialize base agent
        super().__init__("llm_adversarial_agent", config)
        
        # Override logger if provided
        if logger:
            self.logger = logger
        
        self.mcp_factory = mcp_factory
        
        # Initialize LLM reasoning engine (the agent's brain)
        if llm_engine is None:
            self.logger.info("Initializing LLM reasoning engine from config")
            llm_config = load_llm_config(logger=self.logger)
            self.llm_engine = LLMReasoningEngine.from_config(
                config=llm_config,
                logger=self.logger
            )
        else:
            self.llm_engine = llm_engine
        
        # Define available tools for LLM (attack and storage tools)
        self.available_tools = self._define_available_tools()
        
        # Initialize ReAct loop engine
        react_config = config.get("agents", {}).get("adversarial", {})
        self.react_engine = ReActLoopEngine(
            llm_engine=self.llm_engine,
            mcp_factory=self.mcp_factory,
            system_prompt=self.SYSTEM_PROMPT,
            available_tools=self.available_tools,
            max_iterations=0,  # Unlimited iterations (runs until stopped)
            sleep_seconds=0,  # No sleep between iterations - we control timing in the workflow
            logger=self.logger
        )
        
        # Initialize agent state
        if not self.state.get("total_attacks_injected"):
            self.state.set("total_attacks_injected", 0)
        if not self.state.get("last_attack_time"):
            self.state.set("last_attack_time", None)
        if not self.state.get("recent_attack_ids"):
            self.state.set("recent_attack_ids", [])
        
        self.logger.info("LLM Adversarial Agent initialized")
        self.logger.info(f"Available tools: {len(self.available_tools)}")
    
    def run(self):
        """
        Main agent loop using ReAct pattern.
        
        Runs the ReAct loop continuously:
        1. Generate observation (attack state)
        2. LLM reasons about observation
        3. Execute LLM's decided tool calls
        4. Feed results back to LLM
        5. Repeat
        
        The loop continues until self.running is set to False.
        
        Requirements:
        - 4.9: Run continuously using ReAct loop
        """
        self.logger.info("Starting LLM Adversarial Agent ReAct loop")
        
        try:
            # Run ReAct loop with observation generator
            self.react_engine.run_loop(
                get_observation=self._get_observation,
                on_iteration_complete=self._on_iteration_complete
            )
        except Exception as e:
            self.logger.error(f"Error in ReAct loop: {e}", exc_info=True)
            self.statistics.record_failure()
        finally:
            self.logger.info("ReAct loop stopped")

    def run_single_cycle(self):
        """
        Run exactly ONE complete 5-phase attack cycle, then stop.
        
        Phases:
        1. OBSERVE - read PC state
        2. LIST   - list_attack_patterns()
        3. ANALYZE - review options (no tool call)
        4. CHOOSE  - select attack (no tool call)
        5. INJECT  - inject_attack()
        
        After the attack is injected the loop stops automatically
        (no 10-minute wait, no repeat).
        
        Returns:
            Dict with cycle results summary
        """
        self.logger.info("🎯 Starting SINGLE attack cycle (5 phases)...")
        
        # Configure react engine for exactly 5 iterations
        original_max = self.react_engine.max_iterations
        self.react_engine.max_iterations = 5
        self._single_cycle_mode = True
        
        try:
            self.react_engine.run_loop(
                get_observation=self._get_observation,
                on_iteration_complete=self._on_iteration_complete
            )
        except Exception as e:
            self.logger.error(f"Error in single attack cycle: {e}", exc_info=True)
            self.statistics.record_failure()
        finally:
            # Restore original settings
            self.react_engine.max_iterations = original_max
            self._single_cycle_mode = False
            self.logger.info("✅ Single attack cycle finished.")
        
        return {
            'total_attacks_injected': self.state.get('total_attacks_injected', 0),
            'last_attack_time': self.state.get('last_attack_time'),
            'recent_attack_ids': self.state.get('recent_attack_ids', [])[-5:]
        }
    
    def cleanup(self):
        """
        Cleanup resources on shutdown.
        
        Stops ReAct loop and disconnects MCP clients.
        """
        self.logger.info("Cleaning up LLM Adversarial Agent")
        
        # Stop ReAct loop
        if self.react_engine.is_running():
            self.react_engine.stop()
        
        # Save final state
        self.state.save()
        
        self.logger.info("Cleanup complete")

    def _get_observation(self) -> str:
        """
        Generate observation of current attack state AND PC state for LLM.
        
        Creates a natural language description of:
        - Current timestamp
        - Attack state (attacks injected, last attack time)
        - Recent attack IDs (last 10 for context)
        - PC STATE: Recent real events from collectors (user activity, processes, files, network)
        - Error metrics (error count, error rate)
        - Uptime
        - Decision prompts for LLM
        
        This observation provides context for LLM to make intelligent, context-aware attack decisions
        based on actual system activity.
        
        Returns:
            Natural language observation string
        
        Requirements:
        - 4.6: Provide attack state observations to LLM
        - 4.7: Include attacks injected, recent attack IDs, error rates, uptime
        - ENHANCED: Include PC state from collected events for context-aware attacks
        """
        from datetime import datetime, timedelta
        
        # Get current state
        total_attacks = self.state.get("total_attacks_injected", 0)
        last_attack = self.state.get("last_attack_time", "Never")
        recent_ids = self.state.get("recent_attack_ids", [])
        
        # Get statistics
        stats = self.statistics.to_dict()
        uptime_seconds = stats["uptime_seconds"]
        error_count = stats["error_count"]
        error_rate = stats["error_rate_per_minute"]
        operations_completed = stats["operations_completed"]
        operations_failed = stats["operations_failed"]
        
        # Format uptime
        uptime_hours = uptime_seconds / 3600
        uptime_str = f"{uptime_hours:.2f} hours"
        
        # Format recent attack IDs (last 10)
        recent_ids_display = recent_ids[-10:] if len(recent_ids) > 10 else recent_ids
        recent_ids_str = ", ".join(recent_ids_display) if recent_ids_display else "None"
        
        # Query recent PC state from event storage (last 5 minutes of REAL events)
        pc_state_summary = self._get_pc_state_summary()
        
        # Create observation
        observation = f"""CURRENT ATTACK STATE:
Time: {datetime.now().isoformat()}
Uptime: {uptime_str}

ATTACK INJECTION STATUS:
- Total attacks injected: {total_attacks}
- Last attack time: {last_attack}
- Recent attack IDs (last 10): {recent_ids_str}

PC STATE (Last 5 minutes - REAL events from collectors):
{pc_state_summary}

PERFORMANCE METRICS:
- Operations completed: {operations_completed}
- Operations failed: {operations_failed}
- Error count: {error_count}
- Error rate: {error_rate:.2f} errors/minute

DECISION POINTS:
1. What attack strategy should you use now?
2. Which MITRE ATT&CK technique should you select?
3. How should you vary parameters (user_id, device_id, file_paths)?
4. Should you use dataset attacks or generate novel attacks?
5. How should you adapt based on error rates and recent attacks?

Consider the attack state above and decide what actions to take.
Provide your reasoning and then specify which tools to use.
Remember: ALWAYS set is_simulated=True for all attack events."""
        
        return observation
    
    def _get_pc_state_summary(self) -> str:
        """
        Query recent PC state from event storage to provide context for attack decisions.
        
        Queries the last 5 minutes of REAL events (is_simulated=false) to understand:
        - Active users and their behavior
        - Running processes
        - File access patterns
        - Network activity
        - USB device usage
        - System state
        
        This allows the LLM to make context-aware attack decisions like:
        - "User AAM0658 is actively working, inject credential theft now"
        - "USB device detected, inject exfiltration attack"
        - "High network activity, inject data exfiltration via network"
        
        Returns:
            Natural language summary of PC state
        """
        from datetime import datetime, timedelta
        
        try:
            # Query last 5 minutes of REAL events
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=5)
            
            # Use query_events tool via MCP
            query_result = self.mcp_factory.get_client("event_storage").call_tool(
                "query_events",
                {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "filters": {
                        "is_simulated": False  # Only REAL events from collectors
                    },
                    "limit": 100  # Last 100 real events
                }
            )
            
            # FIX: The original code assumed a rigid response envelope:
            #   {"success": True, "result": {"events": [...]}}
            # but the MCP client may return any of several formats depending
            # on the server implementation. We now try all common layouts in
            # order so the method works regardless of which format is used.
            events = None
            
            if isinstance(query_result, dict):
                # Format 1: {"success": bool, "result": {"events": [...]}}
                if query_result.get("success") and isinstance(query_result.get("result"), dict):
                    events = query_result["result"].get("events", [])
                
                # Format 2: {"success": bool, "events": [...]}
                elif query_result.get("success") and "events" in query_result:
                    events = query_result["events"]
                
                # Format 3: {"events": [...]}  (no success wrapper)
                elif "events" in query_result:
                    events = query_result["events"]
                
                # Format 4: {"result": {"events": [...]}}
                elif isinstance(query_result.get("result"), dict):
                    events = query_result["result"].get("events", [])
                
                # Format 5: {"result": [...]}  (result is directly the list)
                elif isinstance(query_result.get("result"), list):
                    events = query_result["result"]
                
                # Format 6: success=False means an actual error from the server
                elif query_result.get("success") is False:
                    err = query_result.get("error", "unknown error")
                    return f"PC State: Event storage returned an error – {err}"
            
            elif isinstance(query_result, list):
                # Format 7: bare list returned directly
                events = query_result
            
            if events is None:
                # Could not recognise the format – log it and fall through
                self.logger.warning(
                    f"Unrecognised query_events response format: "
                    f"{str(query_result)[:200]}"
                )
                return "PC State: Unable to query recent events (unexpected response format)"
            
            if not events:
                return """PC State: No recent activity detected
- System appears idle or collectors not running
- Consider injecting attacks that don't require active user context
- Suggestion: Inject background reconnaissance or scheduled task attacks"""
            
            # Analyze events to build PC state summary
            summary = self._analyze_events_for_context(events)
            return summary
        
        except Exception as e:
            self.logger.warning(f"Failed to query PC state: {e}")
            return f"PC State: Query failed ({str(e)[:50]}...)"
    
    def _analyze_events_for_context(self, events: list) -> str:
        """
        Analyze collected events to build context summary for LLM.
        
        Args:
            events: List of recent real events from collectors
        
        Returns:
            Natural language summary of PC activity
        """
        # Count events by category
        event_counts = {}
        users_active = set()
        devices_seen = set()
        processes_seen = set()
        files_accessed = set()
        network_connections = 0
        usb_devices = set()
        
        for event in events:
            # Count by category
            category = event.get("event_category", "unknown")
            event_counts[category] = event_counts.get(category, 0) + 1
            
            # Track users
            user_id = event.get("user_id")
            if user_id:
                users_active.add(user_id)
            
            # Track devices
            device_id = event.get("device_id")
            if device_id:
                devices_seen.add(device_id)
            
            # Track processes
            if category == "process":
                process_name = event.get("details", {}).get("process_name")
                if process_name:
                    processes_seen.add(process_name)
            
            # Track file access
            if category == "file":
                file_path = event.get("resource")
                if file_path:
                    files_accessed.add(file_path)
            
            # Track network
            if category == "network":
                network_connections += 1
            
            # Track USB devices
            if category == "usb_device":
                usb_id = event.get("details", {}).get("device_id")
                if usb_id:
                    usb_devices.add(usb_id)
        
        # Build summary
        summary_parts = []
        
        # User activity
        if users_active:
            user_list = ", ".join(list(users_active)[:5])
            summary_parts.append(f"- Active users: {user_list} ({len(users_active)} total)")
        else:
            summary_parts.append("- Active users: None detected")
        
        # Device activity
        if devices_seen:
            device_list = ", ".join(list(devices_seen)[:3])
            summary_parts.append(f"- Active devices: {device_list} ({len(devices_seen)} total)")
        
        # Process activity
        if processes_seen:
            process_list = ", ".join(list(processes_seen)[:5])
            summary_parts.append(f"- Running processes: {process_list} ({len(processes_seen)} total)")
        
        # File activity
        if files_accessed:
            summary_parts.append(f"- Files accessed: {len(files_accessed)} unique files")
            # Show a few examples
            file_examples = list(files_accessed)[:3]
            for f in file_examples:
                summary_parts.append(f"  • {f}")
        
        # Network activity
        if network_connections > 0:
            summary_parts.append(f"- Network connections: {network_connections} events")
        
        # USB activity
        if usb_devices:
            usb_list = ", ".join(list(usb_devices)[:3])
            summary_parts.append(f"- USB devices: {usb_list} ({len(usb_devices)} total)")
        
        # Event breakdown
        summary_parts.append(f"- Total events: {len(events)}")
        category_breakdown = ", ".join([f"{cat}: {count}" for cat, count in sorted(event_counts.items())])
        summary_parts.append(f"- Event breakdown: {category_breakdown}")
        
        # Attack suggestions based on context
        suggestions = []
        if usb_devices:
            suggestions.append("USB devices detected → Consider USB exfiltration attacks (T1052.001)")
        if network_connections > 10:
            suggestions.append("High network activity → Consider network exfiltration (T1048.003)")
        if len(files_accessed) > 20:
            suggestions.append("Heavy file activity → Consider data staging attacks (T1074)")
        if len(processes_seen) > 15:
            suggestions.append("Many processes running → Consider credential dumping (T1003)")
        
        if suggestions:
            summary_parts.append("\nATTACK OPPORTUNITIES:")
            for suggestion in suggestions:
                summary_parts.append(f"  • {suggestion}")
        
        return "\n".join(summary_parts)
    
    def _define_available_tools(self) -> list:
        """
        Define available MCP tools in OpenAI function calling format.
        
        Formats attack tools, code execution tool, and storage tools for LLM tool calling.
        Includes MITRE technique descriptions and parameter schemas.
        
        Returns:
            List of tools in OpenAI function calling format
        
        Requirements:
        - 5.1-5.10: MCP Tool Integration for LLM
        """
        tools = [
            # Attack Tool 1: List Attack Patterns
            {
                "type": "function",
                "function": {
                    "name": "list_attack_patterns",
                    "description": (
                        "List available attack patterns from CERT r4.2 insider threat dataset. "
                        "Returns attack IDs, names, categories, and MITRE ATT&CK techniques. "
                        "MITRE Techniques include: T1052.001 (Exfiltration Over USB), "
                        "T1078 (Valid Accounts), T1566 (Phishing), T1485 (Data Destruction), "
                        "T1530 (Data from Cloud Storage), T1213 (Data from Information Repositories)."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": (
                                    "Filter by attack category (optional). Categories: "
                                    "data_exfiltration (T1052.001, T1530), "
                                    "credential_theft (T1078, T1552), "
                                    "sabotage (T1485, T1490), "
                                    "policy_violation (T1213), "
                                    "reconnaissance (T1087, T1083)"
                                ),
                                "enum": ["data_exfiltration", "credential_theft", "sabotage", "policy_violation", "reconnaissance"]
                            }
                        },
                        "required": []
                    }
                }
            },
            
            # Attack Tool 2: Inject Attack
            {
                "type": "function",
                "function": {
                    "name": "inject_attack",
                    "description": (
                        "Inject an attack pattern with customizable parameters. "
                        "Generates realistic attack event sequences based on CERT r4.2 dataset. "
                        "CRITICAL: Always set is_simulated=True to mark events as simulated. "
                        "Use varied user_id and device_id to simulate different attackers."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "attack_id": {
                                "type": "string",
                                "description": (
                                    "Attack pattern ID from list_attack_patterns. "
                                    "Examples: cert_r42_s1_aam0658 (USB Exfiltration), "
                                    "cert_r42_s2_btr0805 (Credential Theft), "
                                    "cert_r42_s3_cmp1200 (Sabotage)"
                                )
                            },
                            "user_id": {
                                "type": "string",
                                "description": (
                                    "User ID for attack simulation. Use realistic IDs like: "
                                    "AAM0658, BTR0805, CMP1200, JDO1234, SMI5678. "
                                    "Vary this to simulate different insider threats."
                                )
                            },
                            "device_id": {
                                "type": "string",
                                "description": (
                                    "Device ID for attack simulation. Use realistic IDs like: "
                                    "PC-1234, LAPTOP-5678, WORKSTATION-9012. "
                                    "Vary this to simulate different attack sources."
                                )
                            },
                            "is_simulated": {
                                "type": "boolean",
                                "description": (
                                    "MUST be True for all attacks. Marks events as simulated "
                                    "to distinguish from real data. Never set to False."
                                )
                            }
                        },
                        "required": ["attack_id", "user_id", "device_id", "is_simulated"]
                    }
                }
            },
            
            # Code Execution Tool: Execute Code in ATTACK_SIMULATION mode
            {
                "type": "function",
                "function": {
                    "name": "execute_code",
                    "description": (
                        "Execute Python code in sandboxed environment with ATTACK_SIMULATION mode. "
                        "Use this to generate novel attack patterns, transform attack data, "
                        "or create custom attack event sequences. "
                        "ATTACK_SIMULATION mode allows: datetime, random, json, hashlib, uuid, base64. "
                        "Always set execution_mode='attack_simulation' for adversarial operations."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": (
                                    "Python code to execute. Can generate attack events, "
                                    "randomize parameters, or create custom attack sequences. "
                                    "Example: Generate random user IDs, create timestamp variations, "
                                    "build custom event payloads."
                                )
                            },
                            "timeout_seconds": {
                                "type": "integer",
                                "description": "Execution timeout in seconds (1-30, default: 10)",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 30
                            },
                            "execution_mode": {
                                "type": "string",
                                "description": (
                                    "Security profile. MUST use 'attack_simulation' for adversarial agent. "
                                    "This mode allows attack-related imports and operations."
                                ),
                                "enum": ["restricted", "attack_simulation"],
                                "default": "attack_simulation"
                            }
                        },
                        "required": ["code"]
                    }
                }
            }
        ]
        
        return tools
    
    def _on_iteration_complete(self, iteration: int, results: Dict[str, Any]):
        """
        Callback after each ReAct loop iteration.
        
        Updates agent state and statistics based on iteration results.
        Tracks total_attacks_injected, last_attack_time, and recent_attack_ids
        based on tool execution results.
        
        Also implements 10-minute wait after attack injection (PHASE 5 complete).
        
        Args:
            iteration: Iteration number
            results: Iteration results dictionary
        
        Requirements:
        - 7.6: Track total_attacks_injected for LLM context
        - 7.7: Track last_attack_time for LLM timing decisions
        - 7.8: Track recent_attack_ids (last 100) to avoid repetition
        - 7.10: Save state after each major operation
        """
        from datetime import datetime
        import time
        
        # Update statistics
        if results.get("errors"):
            self.statistics.record_failure()
        else:
            self.statistics.record_success()
        
        # Update state based on tool results
        tool_results = results.get("tool_results", [])
        attack_injected = False
        
        for tool_result in tool_results:
            tool_name = tool_result.get("name", "")
            result_data = tool_result.get("result", {})
            
            # Track attack injections
            if tool_name == "inject_attack":
                # Check if result contains an error
                if "error" in result_data:
                    error_info = result_data.get("error", {})
                    error_type = error_info.get("type", "unknown")
                    error_message = error_info.get("message", "Unknown error")
                    self.logger.warning(
                        f"⚠️ Attack injection failed: {error_type} - {error_message}"
                    )
                    # Don't update state for failed injections
                    continue
                
                # Success case - extract events and store them
                events = result_data.get("events", [])
                attack_id = result_data.get("attack_id", "")
                
                if events:
                    # Store events in data_agent's event storage
                    try:
                        storage_client = self.mcp_factory.get_client("event_storage")
                        store_result = storage_client.call_tool("store_events", {"events": events})
                        
                        # Parse storage result - handle multiple response formats
                        stored_count = 0
                        if isinstance(store_result, dict):
                            # Try different field names
                            stored_count = (
                                store_result.get("stored_count", 0) or
                                store_result.get("stored", 0) or
                                store_result.get("count", 0)
                            )
                        
                        self.logger.info(
                            f"💾 Stored {stored_count} events in event storage for attack {attack_id}"
                        )
                    except Exception as e:
                        self.logger.error(f"❌ Failed to store events: {e}")
                        # Continue anyway - don't fail the whole injection
                
                # Update state
                # Update last attack time
                self.state.set("last_attack_time", datetime.now().isoformat())
                
                # Update total attacks injected
                current_total = self.state.get("total_attacks_injected", 0)
                new_total = current_total + 1
                self.state.set("total_attacks_injected", new_total)
                
                # Track recent attack IDs (last 100)
                if attack_id:
                    recent_ids = self.state.get("recent_attack_ids", [])
                    recent_ids.append(attack_id)
                    # Keep only last 100
                    if len(recent_ids) > 100:
                        recent_ids = recent_ids[-100:]
                    self.state.set("recent_attack_ids", recent_ids)
                
                events_generated = len(events)
                
                self.logger.info(
                    f"🎯 Attack injected: {attack_id}, "
                    f"generated {events_generated} events, "
                    f"total attacks: {new_total}"
                )
                
                attack_injected = True
        
        # Log iteration summary
        tool_calls = results.get("tool_calls", [])
        successful_calls = sum(1 for tc in tool_calls if tc.get("success", False))
        failed_calls = sum(1 for tc in tool_calls if not tc.get("success", True))
        
        self.logger.info(
            f"Iteration {iteration} complete: "
            f"{successful_calls} tools succeeded, {failed_calls} tools failed, "
            f"duration: {results.get('duration_seconds', 0):.2f}s"
        )
        
        # If attack was injected (PHASE 5 complete)
        if attack_injected:
            if getattr(self, '_single_cycle_mode', False):
                # In single-cycle mode: stop immediately after the injection
                self.logger.info("✅ PHASE 5 complete. Single attack cycle finished.")
                self.react_engine.stop()
            else:
                # In continuous mode: wait 10 minutes before next cycle
                wait_minutes = 10
                wait_seconds = wait_minutes * 60
                self.logger.info(f"⏰ PHASE 5 complete. Waiting {wait_minutes} minutes before next attack cycle...")
                time.sleep(wait_seconds)
                self.logger.info(f"✅ Wait complete. Starting new attack cycle (PHASE 1).")

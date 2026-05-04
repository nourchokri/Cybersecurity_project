"""
MCP Integration - Event Collection with Tracking

CRITICAL EXCERPT: This shows how to track collected events across iterations.

The key is to maintain an `all_collected_events` list that accumulates
events from all collector tool executions, then return it in the final result.
"""

# In run_agent_iteration() method:

def run_agent_iteration(self, collectors: List[str]) -> Dict[str, Any]:
    """
    Run one iteration of the agent's ReAct loop.
    
    CRITICAL: Must return 'collected_events' in the result.
    """
    
    # Initialize event tracking
    all_collected_events = []  # ← CRITICAL: Track events across iterations
    events_by_tool = {}
    tools_executed = []
    
    # ... agent reasoning and tool selection ...
    
    for tool_call in tool_calls:
        tool_name = tool_call.get('name')
        tool_args = tool_call.get('arguments', {})
        
        # Execute the tool
        result = self._execute_tool(tool_name, tool_args)
        
        # Extract events from result
        if isinstance(result, dict) and 'events' in result:
            events_list = result['events']
            if isinstance(events_list, list):
                # ← CRITICAL: Accumulate events
                all_collected_events.extend(events_list)
                events_by_tool[tool_name] = len(events_list)
        
        tools_executed.append(tool_name)
    
    # Return result with collected events
    return {
        'ok': True,
        'llm_reasoning': '...',
        'tools_executed': tools_executed,
        'events_by_tool': events_by_tool,
        'total_events': len(all_collected_events),
        'collected_events': all_collected_events,  # ← CRITICAL: Include actual events
        'timestamp': datetime.now().isoformat(),
    }


# Example of what a collector tool returns:
def collect_system_events():
    """Collector tool that returns events."""
    events = [
        {
            'event_id': 'abc123',
            'timestamp': '2026-05-02T10:00:00',
            'user_id': 'moham',
            'device_id': 'PC01',
            'event_type': 'cpu_usage',
            'event_category': 'system',
            'action': 'monitor',
            'resource': 'cpu',
            'metadata': {'cpu_percent': 45.2},
            'source': 'psutil'
        },
        # ... more events ...
    ]
    
    return {
        'events': events,  # ← List of StandardEvent dictionaries
        'count': len(events),
        'status': 'success'
    }

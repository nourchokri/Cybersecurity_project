"""Direct collector execution without MCP subprocess overhead."""
import logging
from typing import Dict, Any, List
from datetime import datetime
import sys
from pathlib import Path

logger = logging.getLogger('data_agent')

# Add data_agent root to path so collectors can import from each other
data_agent_root = Path(__file__).parent.parent
if str(data_agent_root) not in sys.path:
    sys.path.insert(0, str(data_agent_root))


class DirectCollectorService:
    """Execute collectors directly without MCP subprocess."""
    
    AVAILABLE_COLLECTORS = {
        'system': ('collectors.system_collector', 'collect_system_snapshot'),
        'network': ('collectors.network_collector', 'collect_network_connections'),
        'process': ('collectors.process_collector', 'collect_running_processes'),
        'file': ('collectors.file_collector', 'collect_file_snapshot'),
    }
    
    def collect_all(self) -> Dict[str, Any]:
        """Collect from all available collectors."""
        total_events = 0
        collectors_run = []
        all_events = []
        
        for name, (module_name, func_name) in self.AVAILABLE_COLLECTORS.items():
            try:
                logger.info(f"Running collector: {name}")
                events = self._run_collector(module_name, func_name)
                total_events += len(events)
                collectors_run.append(name)
                all_events.extend(events)
                logger.info(f"Collector {name} collected {len(events)} events")
            except Exception as e:
                logger.warning(f"Collector {name} failed: {e}")
        
        return {
            'events_collected': total_events,
            'collectors': collectors_run,
            'timestamp': datetime.now().isoformat(),
            'events': all_events
        }
    
    def _run_collector(self, module_name: str, func_name: str) -> List[Dict[str, Any]]:
        """Run a single collector module."""
        try:
            # Import the collector module
            module = __import__(module_name, fromlist=[func_name])
            
            # Call the collection function
            if hasattr(module, func_name):
                collect_func = getattr(module, func_name)
                events = collect_func()
                
                # Convert StandardEvent objects to dicts if needed
                if events and hasattr(events[0], 'to_dict'):
                    return [e.to_dict() for e in events]
                elif events and hasattr(events[0], 'model_dump'):
                    return [e.model_dump() for e in events]
                return events if events else []
            else:
                logger.warning(f"Module {module_name} has no {func_name} function")
                return []
                
        except Exception as e:
            logger.error(f"Error running collector {module_name}.{func_name}: {e}", exc_info=True)
            return []

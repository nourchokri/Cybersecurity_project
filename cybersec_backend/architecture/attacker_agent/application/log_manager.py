"""Log Manager for Attacker Agent - Captures and stores logs for frontend display."""
import logging
from collections import deque
from datetime import datetime
from typing import Dict, Any, List
import threading

# Global log buffer (thread-safe)
_log_buffer = deque(maxlen=100)  # Keep last 100 log entries
_log_lock = threading.Lock()


class FrontendLogHandler(logging.Handler):
    """Custom log handler that captures logs for frontend display."""
    
    def emit(self, record):
        """Capture log record and add to buffer."""
        try:
            # Format the log entry
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                'level': record.levelname,
                'message': self.format(record),
                'logger': record.name
            }
            
            # Add to buffer (thread-safe)
            with _log_lock:
                _log_buffer.append(log_entry)
        except Exception:
            self.handleError(record)


def get_recent_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get recent logs from buffer.
    
    Args:
        limit: Maximum number of logs to return
        
    Returns:
        List of log entries
    """
    with _log_lock:
        # Get last N logs
        logs = list(_log_buffer)[-limit:]
        return logs


def clear_logs():
    """Clear all logs from buffer."""
    with _log_lock:
        _log_buffer.clear()


def setup_frontend_logging():
    """Setup logging to capture logs for frontend display."""
    # Get the attacker agent logger
    logger = logging.getLogger('attacker_agent')
    
    # Check if handler already exists
    for handler in logger.handlers:
        if isinstance(handler, FrontendLogHandler):
            return  # Already setup
    
    # Create and add frontend handler
    frontend_handler = FrontendLogHandler()
    frontend_handler.setLevel(logging.INFO)
    
    # Simple format for frontend
    formatter = logging.Formatter('%(message)s')
    frontend_handler.setFormatter(formatter)
    
    logger.addHandler(frontend_handler)
    logger.info('Frontend logging initialized')

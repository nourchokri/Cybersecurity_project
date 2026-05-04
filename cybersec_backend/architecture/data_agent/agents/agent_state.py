"""
Agent State Management

This module provides the AgentState class for persistent state management
across agent restarts. State is automatically saved to JSON files.

It also provides the AgentStatistics class for tracking agent performance metrics.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
import logging


class AgentState:
    """
    Represents the persistent state of an agent.
    
    Provides automatic persistence to JSON files with get/set methods.
    State is saved immediately after each modification to ensure durability.
    
    Attributes:
        state_file: Path to the JSON state file
        data: Dictionary containing the agent's state data
    """
    
    def __init__(self, state_file: Path):
        """
        Initialize AgentState with a state file path.
        
        Args:
            state_file: Path to the JSON file for state persistence
        """
        self.state_file = Path(state_file)
        self.data: Dict[str, Any] = {}
        self.logger = logging.getLogger(f"agent_state.{self.state_file.stem}")
        self.load()
    
    def load(self):
        """
        Load state from file.
        
        If the file doesn't exist, initializes with empty state.
        If the file is corrupted, logs error and initializes with empty state.
        """
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    self.data = json.load(f)
                self.logger.debug(f"Loaded state from {self.state_file}")
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse state file {self.state_file}: {e}")
                self.data = {}
            except Exception as e:
                self.logger.error(f"Failed to load state file {self.state_file}: {e}")
                self.data = {}
        else:
            self.logger.debug(f"State file {self.state_file} does not exist, starting with empty state")
            self.data = {}
    
    def save(self):
        """
        Save state to file.
        
        Creates parent directories if they don't exist.
        Writes state as formatted JSON with 2-space indentation.
        """
        try:
            # Create parent directories if needed
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write state to file with pretty formatting
            with open(self.state_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            
            self.logger.debug(f"Saved state to {self.state_file}")
        except Exception as e:
            self.logger.error(f"Failed to save state to {self.state_file}: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from state.
        
        Args:
            key: State key to retrieve
            default: Default value if key doesn't exist
        
        Returns:
            Value associated with key, or default if key not found
        """
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any):
        """
        Set a value in state and automatically persist to file.
        
        Args:
            key: State key to set
            value: Value to store (must be JSON-serializable)
        
        Raises:
            TypeError: If value is not JSON-serializable
        """
        self.data[key] = value
        self.save()
    
    def update(self, updates: Dict[str, Any]):
        """
        Update multiple state values at once and persist.
        
        Args:
            updates: Dictionary of key-value pairs to update
        
        Raises:
            TypeError: If any value is not JSON-serializable
        """
        self.data.update(updates)
        self.save()
    
    def delete(self, key: str):
        """
        Delete a key from state and persist.
        
        Args:
            key: State key to delete
        """
        if key in self.data:
            del self.data[key]
            self.save()
    
    def clear(self):
        """
        Clear all state data and persist empty state.
        """
        self.data = {}
        self.save()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Get a copy of the entire state as a dictionary.
        
        Returns:
            Copy of the state data dictionary
        """
        return self.data.copy()


class AgentStatistics:
    """
    Tracks agent performance metrics.
    
    Provides tracking for operations completed/failed, error counts,
    error rates, and uptime calculations. Used for monitoring and
    observability of agent behavior.
    
    Attributes:
        start_time: Timestamp when statistics tracking started
        operations_completed: Count of successful operations
        operations_failed: Count of failed operations
        error_count: Total number of errors encountered
        last_operation_time: Timestamp of last operation (success or failure)
        last_error_time: Timestamp of last error
    """
    
    def __init__(self):
        """Initialize AgentStatistics with zero counters and current timestamp."""
        self.start_time = datetime.now()
        self.operations_completed = 0
        self.operations_failed = 0
        self.last_operation_time: Optional[datetime] = None
        self.error_count = 0
        self.last_error_time: Optional[datetime] = None
    
    def record_success(self):
        """
        Record a successful operation.
        
        Increments operations_completed counter and updates last_operation_time.
        """
        self.operations_completed += 1
        self.last_operation_time = datetime.now()
    
    def record_failure(self):
        """
        Record a failed operation.
        
        Increments operations_failed and error_count counters,
        and updates last_operation_time and last_error_time.
        """
        self.operations_failed += 1
        self.error_count += 1
        self.last_operation_time = datetime.now()
        self.last_error_time = datetime.now()
    
    def get_uptime_seconds(self) -> float:
        """
        Calculate uptime in seconds since statistics tracking started.
        
        Returns:
            Number of seconds elapsed since start_time
        """
        return (datetime.now() - self.start_time).total_seconds()
    
    def get_error_rate(self) -> float:
        """
        Calculate error rate as errors per minute.
        
        Returns:
            Number of errors per minute. Returns 0.0 if uptime is zero.
        """
        uptime_minutes = self.get_uptime_seconds() / 60
        if uptime_minutes == 0:
            return 0.0
        return self.error_count / uptime_minutes
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize statistics to a dictionary for JSON serialization.
        
        Returns:
            Dictionary containing all statistics with ISO-formatted timestamps
        """
        return {
            "uptime_seconds": self.get_uptime_seconds(),
            "operations_completed": self.operations_completed,
            "operations_failed": self.operations_failed,
            "error_count": self.error_count,
            "error_rate_per_minute": self.get_error_rate(),
            "last_operation_time": self.last_operation_time.isoformat() if self.last_operation_time else None,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
        }

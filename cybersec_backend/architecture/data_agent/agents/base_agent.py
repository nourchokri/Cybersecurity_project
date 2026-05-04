"""
Base Agent Class

This module provides the BaseAgent abstract class that defines the interface
and common functionality for all autonomous agents.

Features:
- Lifecycle management (start, stop, pause, resume)
- Signal handling (SIGTERM, SIGINT, SIGHUP)
- State persistence via AgentState
- Statistics tracking via AgentStatistics
- Logging with file rotation
- Abstract methods for subclass implementation
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
import signal
import logging
from logging.handlers import RotatingFileHandler

from .agent_state import AgentState, AgentStatistics


class BaseAgent(ABC):
    """
    Abstract base class for all autonomous agents.
    
    Provides common functionality:
    - Lifecycle management (start, stop, pause, resume)
    - State persistence via AgentState
    - Statistics tracking via AgentStatistics
    - Signal handling for graceful shutdown
    - Logging with file rotation
    - Error handling framework
    
    Subclasses must implement:
    - run(): Main agent loop
    - cleanup(): Resource cleanup on shutdown
    
    Attributes:
        name: Agent name (used for logging and state files)
        config: Agent configuration dictionary
        logger: Logger instance with file rotation
        state: AgentState instance for persistent state
        statistics: AgentStatistics instance for performance tracking
        running: Flag indicating if agent is running
        paused: Flag indicating if agent is paused
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize BaseAgent.
        
        Args:
            name: Agent name (used for logging and state files)
            config: Agent configuration dictionary
        """
        self.name = name
        self.config = config
        self.logger = self._setup_logger()
        self.state = AgentState(Path(f"agents/state/{name}.json"))
        self.statistics = AgentStatistics()
        self.running = False
        self.paused = False
        self._setup_signal_handlers()
    
    def _setup_logger(self) -> logging.Logger:
        """
        Configure agent-specific logger with file rotation.
        
        Creates a logger with:
        - Configurable log level from config (default: INFO)
        - File handler with rotation (max 10MB per file, keep 5 files)
        - Formatted output with timestamp, name, level, and message
        
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(self.name)
        logger.setLevel(self.config.get("log_level", "INFO"))
        
        # Prevent duplicate handlers if logger already configured
        if logger.handlers:
            return logger
        
        # Create logs directory
        log_dir = Path("agents/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler (10MB max, keep 5 files)
        log_file = log_dir / f"{self.name}.log"
        handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        
        # Set formatter with timestamp, name, level, and message
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _setup_signal_handlers(self):
        """
        Register signal handlers for graceful shutdown and configuration reload.
        
        Handles:
        - SIGTERM: Graceful shutdown (stop agent)
        - SIGINT: Graceful shutdown (stop agent)
        - SIGHUP: Configuration reload (Unix only)
        
        Note: Signal handlers only work in the main thread. When running in
        Django request threads, this will be skipped silently.
        """
        try:
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            
            # SIGHUP is not available on Windows
            if hasattr(signal, 'SIGHUP'):
                signal.signal(signal.SIGHUP, self._reload_config)
        except ValueError as e:
            # Signal handlers can only be set in the main thread
            # This is expected when running in Django request threads
            self.logger.debug(f"Could not set signal handlers (not in main thread): {e}")
    
    def _signal_handler(self, signum: int, frame):
        """
        Handle shutdown signals (SIGTERM, SIGINT).
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        self.logger.info(f"Received signal {signal_name} ({signum}), stopping agent")
        self.stop()
    
    def _reload_config(self, signum: int, frame):
        """
        Handle configuration reload signal (SIGHUP).
        
        Subclasses can override to implement custom config reload logic.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        self.logger.info("Received SIGHUP, reloading configuration")
        # Subclasses can override to implement config reload
        # Default implementation just logs the signal
    
    def start(self):
        """
        Start the agent.
        
        Sets running flag, updates state, and calls the run() method.
        Handles unhandled exceptions and ensures cleanup on exit.
        """
        self.logger.info(f"Starting agent: {self.name}")
        self.running = True
        self.state.set("status", "running")
        self.state.set("start_time", datetime.now().isoformat())
        
        try:
            self.run()
        except Exception as e:
            self.logger.error(f"Unhandled exception in agent: {e}", exc_info=True)
            self.statistics.record_failure()
        finally:
            self.stop()
    
    def stop(self):
        """
        Stop the agent gracefully.
        
        Sets running flag to False, updates state, and calls cleanup().
        """
        if not self.running:
            return
        
        self.logger.info(f"Stopping agent: {self.name}")
        self.running = False
        self.state.set("status", "stopped")
        self.state.set("stop_time", datetime.now().isoformat())
        self.cleanup()
    
    def pause(self):
        """
        Pause agent execution.
        
        Sets paused flag and updates state. The agent's run() method
        should check the paused flag and skip operations when paused.
        """
        self.logger.info(f"Pausing agent: {self.name}")
        self.paused = True
        self.state.set("status", "paused")
    
    def resume(self):
        """
        Resume agent execution.
        
        Clears paused flag and updates state.
        """
        self.logger.info(f"Resuming agent: {self.name}")
        self.paused = False
        self.state.set("status", "running")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Return current agent statistics.
        
        Returns:
            Dictionary containing agent name, status, and all statistics
        """
        return {
            "agent_name": self.name,
            "status": self.state.get("status", "unknown"),
            **self.statistics.to_dict()
        }
    
    @abstractmethod
    def run(self):
        """
        Main agent loop.
        
        Must be implemented by subclasses. This method should:
        - Check self.running flag to determine when to exit
        - Check self.paused flag to pause operations
        - Implement the agent's core logic
        - Handle errors gracefully
        - Update statistics
        """
        pass
    
    @abstractmethod
    def cleanup(self):
        """
        Cleanup resources on shutdown.
        
        Must be implemented by subclasses. This method should:
        - Close connections to MCP servers
        - Save final state
        - Release any held resources
        - Perform any necessary cleanup operations
        """
        pass

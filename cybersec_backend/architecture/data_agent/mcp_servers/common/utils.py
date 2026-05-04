"""
Shared utilities for MCP servers.

Provides logging, error handling, and validation utilities used across all MCP servers.
"""

import logging
import json
from typing import Any, Dict, Optional
from pathlib import Path
from datetime import datetime


def setup_logger(name: str, log_file: str, level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger for an MCP server.
    
    Args:
        name: Logger name (typically the server name)
        log_file: Path to log file (e.g., 'logs/collector_executor.log')
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def create_error_response(
    error_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a structured error response.
    
    Args:
        error_type: Type of error (e.g., 'validation_error', 'timeout_error')
        message: Human-readable error message
        details: Optional additional error details
    
    Returns:
        Structured error response dictionary
    """
    error_response = {
        "error": {
            "type": error_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    if details:
        error_response["error"]["details"] = details
    
    return error_response


def validate_required_fields(data: Dict[str, Any], required_fields: list[str]) -> tuple[bool, Optional[str]]:
    """
    Validate that required fields are present in data.
    
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    return True, None


def sanitize_path(path: str) -> tuple[bool, Optional[str]]:
    """
    Sanitize file path to prevent directory traversal attacks.
    
    Args:
        path: File path to sanitize
    
    Returns:
        Tuple of (is_safe, error_message)
    """
    if ".." in path:
        return False, "Path contains directory traversal sequence (..)"
    
    if path.startswith("/") or (len(path) > 1 and path[1] == ":"):
        return False, "Absolute paths are not allowed"
    
    return True, None


def serialize_event(event: Any) -> Dict[str, Any]:
    """
    Serialize a StandardEvent Pydantic model to a JSON-compatible dictionary.
    
    Args:
        event: StandardEvent Pydantic model instance
    
    Returns:
        JSON-serializable dictionary
    """
    return event.model_dump(mode='json')


def safe_json_dumps(data: Any, indent: Optional[int] = None) -> str:
    """
    Safely serialize data to JSON string.
    
    Args:
        data: Data to serialize
        indent: Indentation level (None for compact, 2 for readable)
    
    Returns:
        JSON string
    """
    return json.dumps(data, indent=indent, default=str)


def parse_iso8601_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Parse ISO 8601 timestamp string to datetime object.
    
    Args:
        timestamp_str: ISO 8601 formatted timestamp
    
    Returns:
        datetime object or None if parsing fails
    """
    try:
        # Handle both with and without microseconds
        if '.' in timestamp_str:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


def create_success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a structured success response.
    
    Args:
        data: Response data
    
    Returns:
        Structured success response dictionary
    """
    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        **data
    }

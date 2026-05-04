"""
LLM Configuration Loader

This module provides configuration loading and validation for the LLM Reasoning Engine.

Features:
- Load LLM config from agents/config.json
- Validate required fields (api_key, base_url, model)
- Support environment variable overrides
- Provide sensible defaults
- Comprehensive error handling and validation
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path


class LLMConfigError(Exception):
    """Raised when LLM configuration is invalid or missing."""
    pass


class LLMConfig:
    """
    LLM Configuration container with validation.
    
    This class loads and validates LLM configuration from:
    1. agents/config.json file
    2. Environment variable overrides
    3. Sensible defaults
    
    Priority order (highest to lowest):
    1. Environment variables
    2. config.json values
    3. Default values
    
    Attributes:
        api_key: API key for LLM service
        base_url: Base URL for LLM API endpoint
        model: Model name
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens in response
        verify_ssl: Whether to verify SSL certificates
        connection_timeout: Connection timeout in seconds
        request_timeout: Request timeout in seconds
    """
    
    # Default values
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 2000
    DEFAULT_VERIFY_SSL = False
    DEFAULT_CONNECTION_TIMEOUT = 30
    DEFAULT_REQUEST_TIMEOUT = 60
    
    # Environment variable names
    ENV_API_KEY = "LLM_API_KEY"
    ENV_BASE_URL = "LLM_BASE_URL"
    ENV_MODEL = "LLM_MODEL"
    ENV_TEMPERATURE = "LLM_TEMPERATURE"
    ENV_MAX_TOKENS = "LLM_MAX_TOKENS"
    ENV_VERIFY_SSL = "LLM_VERIFY_SSL"
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        verify_ssl: bool = DEFAULT_VERIFY_SSL,
        connection_timeout: int = DEFAULT_CONNECTION_TIMEOUT,
        request_timeout: int = DEFAULT_REQUEST_TIMEOUT
    ):
        """
        Initialize LLM configuration.
        
        Args:
            api_key: API key for LLM service (required)
            base_url: Base URL for LLM API endpoint (required)
            model: Model name (required)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
            verify_ssl: Whether to verify SSL certificates
            connection_timeout: Connection timeout in seconds
            request_timeout: Request timeout in seconds
        
        Raises:
            LLMConfigError: If required fields are missing or invalid
        """
        # Validate required fields
        if not api_key:
            raise LLMConfigError("api_key is required")
        if not base_url:
            raise LLMConfigError("base_url is required")
        if not model:
            raise LLMConfigError("model is required")
        
        # Validate temperature
        if not 0.0 <= temperature <= 1.0:
            raise LLMConfigError(f"temperature must be between 0.0 and 1.0, got {temperature}")
        
        # Validate max_tokens
        if max_tokens <= 0:
            raise LLMConfigError(f"max_tokens must be positive, got {max_tokens}")
        
        # Validate timeouts
        if connection_timeout <= 0:
            raise LLMConfigError(f"connection_timeout must be positive, got {connection_timeout}")
        if request_timeout <= 0:
            raise LLMConfigError(f"request_timeout must be positive, got {request_timeout}")
        
        # Set attributes
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')  # Remove trailing slash
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.verify_ssl = verify_ssl
        self.connection_timeout = connection_timeout
        self.request_timeout = request_timeout
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of configuration
        """
        return {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "verify_ssl": self.verify_ssl,
            "connection_timeout": self.connection_timeout,
            "request_timeout": self.request_timeout
        }
    
    def __repr__(self) -> str:
        """String representation (hides API key)."""
        return (
            f"LLMConfig(base_url='{self.base_url}', model='{self.model}', "
            f"temperature={self.temperature}, max_tokens={self.max_tokens}, "
            f"verify_ssl={self.verify_ssl})"
        )


def load_llm_config(
    config_path: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> LLMConfig:
    """
    Load LLM configuration from file and environment variables.
    
    Configuration priority (highest to lowest):
    1. Environment variables (LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, etc.)
    2. config.json file values
    3. Default values
    
    Args:
        config_path: Path to config.json file (default: agents/config.json)
        logger: Optional logger instance
    
    Returns:
        LLMConfig instance with validated configuration
    
    Raises:
        LLMConfigError: If configuration is invalid or required fields are missing
    
    Example:
        >>> config = load_llm_config()
        >>> print(config.model)
        'hosted_vllm/Llama-3.1-70B-Instruct'
    """
    logger = logger or logging.getLogger("llm_config")
    
    # Determine config file path
    if config_path is None:
        config_path = Path("agents/config.json")
    else:
        config_path = Path(config_path)
    
    # Load from file if exists
    file_config = {}
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                full_config = json.load(f)
                file_config = full_config.get("llm", {})
            logger.info(f"Loaded LLM config from {config_path}")
        except json.JSONDecodeError as e:
            raise LLMConfigError(f"Invalid JSON in {config_path}: {e}")
        except Exception as e:
            raise LLMConfigError(f"Failed to read {config_path}: {e}")
    else:
        logger.debug(f"Config file not found: {config_path}, using environment variables and defaults")
    
    # Get values with priority: env vars > file > defaults
    api_key = os.getenv(LLMConfig.ENV_API_KEY) or file_config.get("api_key", "")
    base_url = os.getenv(LLMConfig.ENV_BASE_URL) or file_config.get("base_url", "")
    model = os.getenv(LLMConfig.ENV_MODEL) or file_config.get("model", "")
    
    # Parse temperature from env (string to float)
    temperature_str = os.getenv(LLMConfig.ENV_TEMPERATURE)
    if temperature_str:
        try:
            temperature = float(temperature_str)
        except ValueError:
            raise LLMConfigError(f"Invalid {LLMConfig.ENV_TEMPERATURE}: {temperature_str}")
    else:
        temperature = file_config.get("temperature", LLMConfig.DEFAULT_TEMPERATURE)
    
    # Parse max_tokens from env (string to int)
    max_tokens_str = os.getenv(LLMConfig.ENV_MAX_TOKENS)
    if max_tokens_str:
        try:
            max_tokens = int(max_tokens_str)
        except ValueError:
            raise LLMConfigError(f"Invalid {LLMConfig.ENV_MAX_TOKENS}: {max_tokens_str}")
    else:
        max_tokens = file_config.get("max_tokens", LLMConfig.DEFAULT_MAX_TOKENS)
    
    # Parse verify_ssl from env (string to bool)
    verify_ssl_str = os.getenv(LLMConfig.ENV_VERIFY_SSL)
    if verify_ssl_str:
        verify_ssl = verify_ssl_str.lower() in ("true", "1", "yes")
    else:
        verify_ssl = file_config.get("verify_ssl", LLMConfig.DEFAULT_VERIFY_SSL)
    
    # Get timeouts (no env var overrides for these)
    connection_timeout = file_config.get("connection_timeout", LLMConfig.DEFAULT_CONNECTION_TIMEOUT)
    request_timeout = file_config.get("request_timeout", LLMConfig.DEFAULT_REQUEST_TIMEOUT)
    
    # Log configuration source
    if os.getenv(LLMConfig.ENV_API_KEY):
        logger.info("Using LLM_API_KEY from environment")
    if os.getenv(LLMConfig.ENV_BASE_URL):
        logger.info("Using LLM_BASE_URL from environment")
    if os.getenv(LLMConfig.ENV_MODEL):
        logger.info("Using LLM_MODEL from environment")
    
    # Create and validate config
    try:
        config = LLMConfig(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            verify_ssl=verify_ssl,
            connection_timeout=connection_timeout,
            request_timeout=request_timeout
        )
        logger.info(f"LLM configuration loaded successfully: {config}")
        return config
    
    except LLMConfigError as e:
        logger.error(f"LLM configuration validation failed: {e}")
        raise


def create_default_config(output_path: str = "agents/config.json"):
    """
    Create a default config.json file with example LLM configuration.
    
    This is a utility function to help users get started with configuration.
    
    Args:
        output_path: Path where config.json should be created
    
    Example:
        >>> create_default_config()
        Created default config at agents/config.json
    """
    default_config = {
        "llm": {
            "api_key": "sk-99f9c57b76a24384bb38d1380de94de6",
            "base_url": "https://tokenfactory.esprit.tn/api",
            "model": "hosted_vllm/Llama-3.1-70B-Instruct",
            "temperature": 0.7,
            "max_tokens": 2000,
            "verify_ssl": False,
            "connection_timeout": 30,
            "request_timeout": 60
        },
        "mcp_servers": {
            "collector_executor": {
                "command": ["python", "-m", "mcp_servers.collector_executor"],
                "connection_timeout": 30,
                "request_timeout": 60
            },
            "event_storage": {
                "command": ["python", "-m", "mcp_servers.event_storage"],
                "connection_timeout": 30,
                "request_timeout": 60
            },
            "attack_injector": {
                "command": ["python", "-m", "mcp_servers.attack_injector"],
                "connection_timeout": 30,
                "request_timeout": 60
            },
            "python_executor": {
                "command": ["python", "-m", "mcp_servers.python_executor"],
                "connection_timeout": 30,
                "request_timeout": 60
            }
        },
        "agents": {
            "data_engineering": {
                "collection_interval_seconds": 300,
                "export_interval_seconds": 3600,
                "max_concurrent_collectors": 5,
                "hours_back": 24,
                "max_retries": 1,
                "retry_delay_seconds": 2
            },
            "adversarial": {
                "attack_interval_seconds": 600,
                "max_attacks_per_cycle": 5,
                "max_retries": 1,
                "retry_delay_seconds": 2
            }
        }
    }
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(default_config, f, indent=2)
    
    print(f"Created default config at {output_path}")


if __name__ == "__main__":
    # Example usage and testing
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) > 1 and sys.argv[1] == "create-default":
        create_default_config()
    else:
        try:
            config = load_llm_config()
            print(f"Successfully loaded LLM config: {config}")
            print(f"API Key: {config.api_key[:10]}...")
            print(f"Base URL: {config.base_url}")
            print(f"Model: {config.model}")
        except LLMConfigError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

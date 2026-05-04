"""
MCP Client Factory

Factory pattern implementation for creating and managing MCP client instances.
Provides client creation from configuration, connection pooling, health checking,
and automatic reconnection for all 4 MCP servers.
"""

from typing import Dict, Any, Optional
import logging
import time
from architecture.data_agent.agents.mcp_client import MCPClient, MCPConnectionError


class MCPClientFactory:
    """
    Factory for creating and managing MCP client instances.
    
    Features:
    - Client creation from configuration
    - Connection pooling (reuse existing clients)
    - Health checking and automatic reconnection
    - Support for all 4 MCP servers:
      * collector_executor (11 collector tools)
      * event_storage (4 storage/query tools)
      * attack_injector (3 attack simulation tools)
      * python_executor (2 code execution tools)
    
    Requirements:
    - 4.8: Factory pattern for creating MCP client instances
    - 12.1: Connect to Collector-Executor MCP server
    - 12.2: Connect to Event-Storage MCP server
    - 12.3: Connect to Attack-Injector MCP server
    - 12.4: Connect to Python-Executor MCP server
    """
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        Initialize MCP client factory.
        
        Args:
            config: Configuration dictionary containing mcp_servers section
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger("mcp_client_factory")
        self.clients: Dict[str, MCPClient] = {}
        
        # Validate configuration
        if "mcp_servers" not in config:
            raise ValueError("Configuration missing 'mcp_servers' section")
        
        self.logger.info("MCPClientFactory initialized")
    
    def get_client(self, server_name: str) -> MCPClient:
        """
        Get or create MCP client for specified server.
        
        Implements connection pooling: reuses existing healthy clients,
        reconnects unhealthy clients, and creates new clients as needed.
        
        Args:
            server_name: Name of MCP server (e.g., "collector_executor", 
                        "event_storage", "attack_injector", "python_executor")
        
        Returns:
            Connected MCP client instance
        
        Raises:
            ValueError: If server_name is not configured
            MCPConnectionError: If connection fails after retries
        """
        # Check if we have an existing client
        if server_name in self.clients:
            client = self.clients[server_name]
            
            # Health check: reuse if healthy
            if client.is_healthy():
                self.logger.debug(f"Reusing existing client for {server_name}")
                return client
            else:
                # Unhealthy client: attempt reconnection
                self.logger.warning(f"Client {server_name} unhealthy, attempting reconnection")
                try:
                    client.restart()
                    self.logger.info(f"Successfully reconnected to {server_name}")
                    return client
                except Exception as e:
                    self.logger.error(f"Reconnection failed for {server_name}: {e}")
                    # Remove failed client and create new one below
                    client.disconnect()
                    del self.clients[server_name]
        
        # Create new client
        self.logger.info(f"Creating new client for {server_name}")
        client = self._create_client(server_name)
        
        # Store in pool
        self.clients[server_name] = client
        return client
    
    def _create_client(self, server_name: str) -> MCPClient:
        """
        Create and connect a new MCP client from configuration.
        
        Args:
            server_name: Name of MCP server
        
        Returns:
            Connected MCP client instance
        
        Raises:
            ValueError: If server configuration not found
            MCPConnectionError: If connection fails
        """
        # Get server configuration
        server_config = self.config.get("mcp_servers", {}).get(server_name)
        if not server_config:
            raise ValueError(f"No configuration for MCP server: {server_name}")
        
        # Validate required fields
        if "command" not in server_config:
            raise ValueError(f"Server {server_name} missing 'command' in configuration")
        
        # Extract configuration parameters
        command = server_config["command"]
        args = server_config.get("args", [])
        
        # Combine command and args into full command list
        full_command = [command] + args
        
        connection_timeout = server_config.get("connection_timeout", 30)
        request_timeout = server_config.get("request_timeout", 60)
        cwd = server_config.get("cwd")  # Optional custom working directory
        
        # Create client
        client = MCPClient(
            server_name=server_name,
            command=full_command,
            connection_timeout=connection_timeout,
            request_timeout=request_timeout,
            cwd=cwd,
            logger=self.logger
        )
        
        # Connect with retry logic
        max_retries = self.config.get("max_connection_retries", 3)
        retry_delay = self.config.get("connection_retry_delay_seconds", 2)
        
        last_error = None
        for attempt in range(max_retries):
            try:
                client.connect()
                self.logger.info(f"Successfully connected to {server_name} (attempt {attempt + 1})")
                return client
            except MCPConnectionError as e:
                last_error = e
                self.logger.warning(
                    f"Connection attempt {attempt + 1}/{max_retries} failed for {server_name}: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        
        # All retries failed
        error_msg = f"Failed to connect to {server_name} after {max_retries} attempts"
        if last_error:
            error_msg += f": {last_error}"
        raise MCPConnectionError(error_msg)
    
    def disconnect_all(self):
        """
        Disconnect all MCP clients and clear the connection pool.
        
        Should be called during agent shutdown to cleanup resources.
        """
        self.logger.info(f"Disconnecting all clients ({len(self.clients)} active)")
        
        for server_name, client in self.clients.items():
            try:
                self.logger.debug(f"Disconnecting {server_name}")
                client.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting {server_name}: {e}")
        
        self.clients.clear()
        self.logger.info("All clients disconnected")
    
    def get_all_clients(self) -> Dict[str, MCPClient]:
        """
        Get all active clients in the connection pool.
        
        Returns:
            Dictionary mapping server names to client instances
        """
        return self.clients.copy()
    
    def health_check_all(self) -> Dict[str, bool]:
        """
        Perform health check on all active clients.
        
        Returns:
            Dictionary mapping server names to health status (True/False)
        """
        health_status = {}
        
        for server_name, client in self.clients.items():
            try:
                is_healthy = client.is_healthy()
                health_status[server_name] = is_healthy
                self.logger.debug(f"Health check {server_name}: {'healthy' if is_healthy else 'unhealthy'}")
            except Exception as e:
                self.logger.error(f"Health check failed for {server_name}: {e}")
                health_status[server_name] = False
        
        return health_status
    
    def reconnect_unhealthy(self) -> Dict[str, bool]:
        """
        Reconnect all unhealthy clients.
        
        Returns:
            Dictionary mapping server names to reconnection success status
        """
        reconnect_results = {}
        health_status = self.health_check_all()
        
        for server_name, is_healthy in health_status.items():
            if not is_healthy:
                self.logger.info(f"Attempting to reconnect unhealthy client: {server_name}")
                try:
                    client = self.clients[server_name]
                    client.restart()
                    reconnect_results[server_name] = True
                    self.logger.info(f"Successfully reconnected {server_name}")
                except Exception as e:
                    self.logger.error(f"Failed to reconnect {server_name}: {e}")
                    reconnect_results[server_name] = False
        
        return reconnect_results

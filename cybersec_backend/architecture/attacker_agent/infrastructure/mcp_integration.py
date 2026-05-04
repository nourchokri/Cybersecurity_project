"""MCP Integration for Attacker Agent."""
import logging
from typing import Dict, Any

logger = logging.getLogger('attacker_agent')


class AttackerMCPManager:
    """
    Manages MCP client connections for the Attacker Agent.
    
    This manager handles connections to:
    - attack_injector: Attack pattern generation (attacker_agent's own MCP)
    
    Note: event_storage is accessed via data_agent's MCPClientManager
    """
    
    def __init__(self):
        """Initialize MCP client manager."""
        from architecture.data_agent.agents.mcp_client_factory import MCPClientFactory
        from pathlib import Path
        
        # Get cybersec_backend root directory
        # __file__ is: cybersec_backend/architecture/attacker_agent/infrastructure/mcp_integration.py
        backend_root = Path(__file__).parent.parent.parent.parent
        
        # MCP server configurations
        self._config = {
            'mcp_servers': {
                'attack_injector': {
                    'command': 'python',
                    'args': [
                        '-m',
                        'architecture.attacker_agent.mcp_servers.attack_injector.server'
                    ],
                    'cwd': str(backend_root),  # Run from cybersec_backend directory
                    'env': {
                        'PYTHONPATH': str(backend_root)
                    }
                }
            }
        }
        
        # Create factory for MCP clients with config
        self._factory = MCPClientFactory(config=self._config, logger=logger)
        
        logger.info('AttackerMCPManager initialized')
        logger.info(f'Backend root: {backend_root}')
    
    def call_attack_injector(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call attack_injector MCP tool.
        
        Args:
            tool_name: Tool name (list_attack_patterns, inject_attack, etc.)
            params: Tool parameters
            
        Returns:
            Tool execution result
        """
        try:
            # Get or create MCP client
            client = self._factory.get_client('attack_injector')
            
            # Call tool
            result = client.call_tool(tool_name, params)
            
            logger.info(f'Called attack_injector.{tool_name} successfully')
            return result
            
        except Exception as e:
            logger.error(f'Failed to call attack_injector.{tool_name}: {e}')
            raise
    
    def get_client(self, server_name: str):
        """
        Get MCP client for a specific server.
        
        Args:
            server_name: Server name (e.g., 'attack_injector')
            
        Returns:
            MCP client instance
        """
        if server_name not in self._config['mcp_servers']:
            raise ValueError(f'Unknown MCP server: {server_name}')
        
        return self._factory.get_client(server_name)
    
    def disconnect_all(self):
        """Disconnect all MCP clients."""
        try:
            self._factory.disconnect_all()
            logger.info('All MCP clients disconnected')
        except Exception as e:
            logger.error(f'Error disconnecting MCP clients: {e}')


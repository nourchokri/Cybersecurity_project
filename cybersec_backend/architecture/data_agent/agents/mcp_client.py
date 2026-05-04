"""
MCP Client Implementation

Custom JSON-RPC 2.0 client for communicating with MCP servers via subprocess
and stdio transport. Provides subprocess lifecycle management, request/response
handling with timeouts, and tool discovery/invocation.
"""

import subprocess
import json
import threading
import queue
import time
from typing import Dict, Any, Optional, List
import logging


class MCPClientError(Exception):
    """Base exception for MCP client errors."""
    pass


class MCPConnectionError(MCPClientError):
    """Raised when connection to MCP server fails."""
    pass


class MCPTimeoutError(MCPClientError):
    """Raised when MCP request times out."""
    pass


class MCPClient:
    """
    Custom MCP client that communicates with MCP servers via subprocess
    and JSON-RPC 2.0 protocol over stdio transport.
    
    Features:
    - Subprocess lifecycle management (start, stop, restart)
    - JSON-RPC 2.0 protocol implementation
    - Request/response handling with timeouts
    - Background reader thread for async response handling
    - Tool discovery via tools/list
    - Tool invocation via tools/call
    - Structured error handling
    - Comprehensive logging
    """
    
    def __init__(self, server_name: str, command: List[str], 
                 connection_timeout: int = 30,
                 request_timeout: int = 60,
                 cwd: Optional[str] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize MCP client.
        
        Args:
            server_name: Name of the MCP server (for logging)
            command: Command to start MCP server (e.g., ["python", "-m", "mcp_servers.collector_executor"])
            connection_timeout: Seconds to wait for server startup (default: 30)
            request_timeout: Default timeout for tool invocations (default: 60)
            cwd: Working directory for MCP server process (default: data_agent root)
            logger: Optional logger instance
        """
        self.server_name = server_name
        self.command = command
        self.connection_timeout = connection_timeout
        self.request_timeout = request_timeout
        self.cwd = cwd
        self.logger = logger or logging.getLogger(f"mcp_client.{server_name}")
        
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self.pending_requests: Dict[int, queue.Queue] = {}
        self.tools: List[Dict[str, Any]] = []
        self.connected = False
        
        # Reader thread for background response handling
        self.reader_thread: Optional[threading.Thread] = None
        self.stop_reader = threading.Event()
    
    def connect(self):
        """
        Start MCP server subprocess and establish connection.
        
        Raises:
            MCPConnectionError: If connection fails or times out
        """
        self.logger.info(f"Connecting to MCP server: {self.server_name}")
        
        try:
            # Replace "python" in command with sys.executable to use current Python
            import sys
            command = self.command.copy()
            if command[0] == "python":
                command[0] = sys.executable
                self.logger.debug(f"Using Python executable: {sys.executable}")
            
            # Set working directory
            # Use custom cwd if provided, otherwise default to data_agent root
            from pathlib import Path
            if self.cwd:
                cwd = self.cwd
                self.logger.debug(f"Using custom working directory: {cwd}")
            else:
                data_agent_root = Path(__file__).parent.parent
                cwd = str(data_agent_root)
                self.logger.debug(f"Using default working directory (data_agent): {cwd}")
            
            # Start subprocess with stdio pipes
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=cwd  # Set working directory
            )
            
            self.logger.debug(f"Started subprocess with PID: {self.process.pid}")
            
            # Start background reader thread
            self.stop_reader.clear()
            self.reader_thread = threading.Thread(
                target=self._read_responses, 
                daemon=True,
                name=f"MCPReader-{self.server_name}"
            )
            self.reader_thread.start()
            
            # Wait for server to be ready (send initialize handshake first)
            start_time = time.time()
            last_error = None
            
            # Step 1: Send initialize request (MCP protocol requirement)
            self.logger.debug("Sending initialize request...")
            try:
                init_result = self._send_request("initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "mcp-client",
                        "version": "1.0.0"
                    }
                }, timeout=10, skip_connection_check=True)  # Skip check for initialize
                
                self.logger.debug(f"Initialize response: {init_result}")
                
                # Step 2: Send initialized notification (no response expected)
                # Note: Notifications don't have an ID and don't expect a response
                self.logger.debug("Sending initialized notification...")
                notif = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }
                notif_json = json.dumps(notif) + "\n"
                self.process.stdin.write(notif_json)
                self.process.stdin.flush()
                
                # Brief pause to let server process notification
                time.sleep(0.1)
                
                # Step 3: Now we can discover tools
                self.logger.debug("Discovering tools...")
                # Use skip_connection_check since we're still in the connection process
                tools_result = self._send_request("tools/list", {}, timeout=10, skip_connection_check=True)
                self.tools = tools_result.get("tools", [])
                self.connected = True
                self.logger.info(
                    f"Connected to {self.server_name}, discovered {len(self.tools)} tools"
                )
                return
                
            except Exception as e:
                last_error = e
                self.logger.error(f"Initialization failed: {e}", exc_info=True)
            
            # Connection failed
            error_msg = f"Failed to connect to {self.server_name} within {self.connection_timeout}s"
            if last_error:
                error_msg += f": {last_error}"
            raise MCPConnectionError(error_msg)
        
        except MCPConnectionError:
            self.disconnect()
            raise
        except Exception as e:
            self.logger.error(f"Connection error: {e}", exc_info=True)
            self.disconnect()
            raise MCPConnectionError(f"Failed to start {self.server_name}: {e}")
    
    def disconnect(self):
        """Stop MCP server subprocess and cleanup resources."""
        self.logger.info(f"Disconnecting from MCP server: {self.server_name}")
        self.connected = False
        
        # Stop reader thread
        if self.reader_thread and self.reader_thread.is_alive():
            self.stop_reader.set()
            self.reader_thread.join(timeout=2)
            if self.reader_thread.is_alive():
                self.logger.warning("Reader thread did not stop gracefully")
        
        # Terminate subprocess
        if self.process:
            self.logger.debug(f"Terminating subprocess PID: {self.process.pid}")
            self.process.terminate()
            
            try:
                self.process.wait(timeout=5)
                self.logger.debug("Subprocess terminated gracefully")
            except subprocess.TimeoutExpired:
                self.logger.warning("Subprocess did not terminate, killing")
                self.process.kill()
                self.process.wait()
            
            self.process = None
        
        # Clear pending requests
        self.pending_requests.clear()
    
    def restart(self):
        """
        Restart the MCP server subprocess.
        
        Raises:
            MCPConnectionError: If restart fails
        """
        self.logger.info(f"Restarting MCP server: {self.server_name}")
        self.disconnect()
        time.sleep(1)  # Brief pause before restart
        self.connect()
    
    def _read_responses(self):
        """
        Background thread to read JSON-RPC responses from server stdout.
        
        Continuously reads lines from subprocess stdout, parses JSON-RPC responses,
        and routes them to the appropriate pending request queue.
        """
        self.logger.debug("Reader thread started")
        
        while not self.stop_reader.is_set() and self.process:
            try:
                # Check if process is still alive
                if self.process.poll() is not None:
                    self.logger.warning(
                        f"Subprocess terminated with code: {self.process.returncode}"
                    )
                    break
                
                # Read line from stdout (this blocks until a line is available)
                line = self.process.stdout.readline()
                
                if not line:
                    # EOF reached
                    self.logger.debug("EOF reached on stdout")
                    break
                
                line = line.strip()
                if not line:
                    # Empty line, skip
                    continue
                
                self.logger.debug(f"Read line: {line[:200]}...")
                
                # Parse JSON-RPC response
                try:
                    response = json.loads(line)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Invalid JSON from server: {line[:100]} - {e}")
                    continue
                
                request_id = response.get("id")
                
                self.logger.debug(f"Received response for request ID: {request_id}")
                
                # Route response to pending request
                if request_id in self.pending_requests:
                    self.pending_requests[request_id].put(response)
                    self.logger.debug(f"Routed response to request ID {request_id}")
                elif request_id is None:
                    # Notification (no ID), log and ignore
                    self.logger.debug(f"Received notification: {response.get('method', 'unknown')}")
                else:
                    self.logger.warning(f"Received response for unknown request ID: {request_id}")
            
            except Exception as e:
                if not self.stop_reader.is_set():
                    self.logger.error(f"Error reading response: {e}", exc_info=True)
                break
        
        self.logger.debug("Reader thread stopped")
    
    def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None, 
                     timeout: Optional[int] = None, skip_connection_check: bool = False) -> Dict[str, Any]:
        """
        Send JSON-RPC 2.0 request and wait for response.
        
        Args:
            method: JSON-RPC method name (e.g., "tools/list", "tools/call")
            params: Method parameters (optional)
            timeout: Request timeout in seconds (uses default if None)
            skip_connection_check: Skip the connection check (for initialize request)
        
        Returns:
            JSON-RPC result object
        
        Raises:
            MCPClientError: If not connected or request fails
            MCPTimeoutError: If request times out
        """
        if not skip_connection_check and (not self.connected or not self.process):
            raise MCPClientError("Not connected to MCP server")
        
        if not self.process:
            raise MCPClientError("No subprocess running")
        
        # Generate unique request ID
        self.request_id += 1
        current_request_id = self.request_id
        
        # Build JSON-RPC 2.0 request
        request = {
            "jsonrpc": "2.0",
            "id": current_request_id,
            "method": method,
            "params": params or {}
        }
        
        # Create response queue for this request
        response_queue = queue.Queue()
        self.pending_requests[current_request_id] = response_queue
        
        try:
            # Send request to subprocess stdin
            request_json = json.dumps(request) + "\n"
            self.logger.debug(f"Sending request ID {current_request_id}: {method}")
            self.logger.debug(f"Request params: {params}")
            
            self.process.stdin.write(request_json)
            self.process.stdin.flush()
            
            # Wait for response with timeout
            timeout_seconds = timeout or self.request_timeout
            try:
                response = response_queue.get(timeout=timeout_seconds)
                self.logger.debug(f"Received response for request ID {current_request_id}")
            except queue.Empty:
                error_msg = f"Request {method} (ID {current_request_id}) timed out after {timeout_seconds}s"
                self.logger.error(error_msg)
                raise MCPTimeoutError(error_msg)
            
            # Check for JSON-RPC error response
            if "error" in response:
                error = response["error"]
                error_msg = f"MCP error: {error.get('message', 'Unknown error')}"
                error_code = error.get('code', 'N/A')
                error_data = error.get('data', {})
                
                self.logger.error(
                    f"JSON-RPC error (code {error_code}): {error_msg}, data: {error_data}"
                )
                raise MCPClientError(error_msg)
            
            # Return result
            result = response.get("result", {})
            self.logger.debug(f"Request {method} completed successfully")
            return result
        
        finally:
            # Cleanup pending request
            self.pending_requests.pop(current_request_id, None)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        Discover available tools from MCP server via tools/list.
        
        Returns:
            List of tool definitions with name, description, and input schema
        
        Raises:
            MCPClientError: If request fails
            MCPTimeoutError: If request times out
        """
        self.logger.debug("Discovering tools via tools/list")
        result = self._send_request("tools/list")
        tools = result.get("tools", [])
        self.logger.info(f"Discovered {len(tools)} tools from {self.server_name}")
        return tools
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any], 
                  timeout: Optional[int] = None) -> Any:
        """
        Invoke an MCP tool via tools/call.
        
        Args:
            tool_name: Name of the tool to invoke
            arguments: Tool arguments (must match tool's input schema)
            timeout: Request timeout in seconds (optional)
        
        Returns:
            Tool result (parsed from JSON response)
        
        Raises:
            MCPClientError: If tool invocation fails
            MCPTimeoutError: If tool invocation times out
        """
        self.logger.info(f"Calling tool: {tool_name}")
        self.logger.debug(f"Tool arguments: {arguments}")
        
        result = self._send_request(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
            timeout=timeout
        )
        
        # Parse result from MCP TextContent format
        # MCP servers return: {"content": [{"type": "text", "text": "<json>"}]}
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if isinstance(content, list) and len(content) > 0:
                text_content = content[0].get("text", "{}")
                try:
                    parsed_result = json.loads(text_content)
                    self.logger.debug(f"Tool {tool_name} returned: {type(parsed_result)}")
                    return parsed_result
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse tool result: {e}")
                    return text_content
        
        # Fallback: return raw result
        self.logger.debug(f"Tool {tool_name} returned raw result")
        return result
    
    def is_healthy(self) -> bool:
        """
        Check if MCP server is responsive.
        
        Returns:
            True if server responds to tools/list, False otherwise
        """
        if not self.connected or not self.process:
            return False
        
        if self.process.poll() is not None:
            self.logger.warning(f"Subprocess has terminated (code: {self.process.returncode})")
            return False
        
        try:
            self.list_tools()
            return True
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
            return False

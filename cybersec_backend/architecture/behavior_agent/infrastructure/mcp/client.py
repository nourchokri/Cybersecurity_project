"""
MCP client for Behavior Agent — mirrors the Risk Decision Agent's client pattern exactly.

Spawns the MCP server as a subprocess and communicates via stdio.
Thread-safe, synchronous wrapper around the async MCP session.
"""

from __future__ import annotations

import asyncio
import json
import sys
import threading
import atexit
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _parse_json_maybe(text: str) -> Any:
    s = (text or '').strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return s


@dataclass(frozen=True)
class McpServerSpec:
    command: str
    args: Tuple[str, ...]


class McpToolClient:
    """Thread-safe synchronous wrapper around a single MCP stdio session."""

    def __init__(self, *, server: McpServerSpec, timeout_sec: float = 30.0) -> None:
        self._server      = server
        self._timeout_sec = float(timeout_sec)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ready       = threading.Event()
        self._lock        = threading.Lock()
        self._init_error: Optional[BaseException] = None
        self._session: Optional[ClientSession] = None
        self._stdio_cm    = None
        self._closed      = False
        self._start()

    def _start(self) -> None:
        t = threading.Thread(target=self._run_thread, name='mcp-behavior-client', daemon=True)
        self._thread = t
        t.start()
        if not self._ready.wait(timeout=self._timeout_sec):
            raise TimeoutError('Timed out starting MCP client session')
        if self._init_error is not None:
            raise RuntimeError(f'Failed to start MCP client: {self._init_error}')

    def _run_thread(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            try:
                loop.run_until_complete(self._async_init())
            except BaseException as e:
                self._init_error = e
                self._ready.set()
                return
            self._ready.set()
            loop.run_forever()
        finally:
            try:
                loop.run_until_complete(self._async_close())
            except Exception:
                pass
            try:
                loop.close()
            except Exception:
                pass

    async def _async_init(self) -> None:
        params = StdioServerParameters(command=self._server.command, args=list(self._server.args))
        self._stdio_cm = stdio_client(params)
        self._read, self._write = await self._stdio_cm.__aenter__()
        self._session = ClientSession(self._read, self._write)
        await self._session.__aenter__()
        await self._session.initialize()

    async def _async_close(self) -> None:
        if self._session is not None:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                pass
            self._session = None
        if self._stdio_cm is not None:
            try:
                await self._stdio_cm.__aexit__(None, None, None)
            except Exception:
                pass
            self._stdio_cm = None

    def call_tool(self, tool_name: str, args: Optional[Dict[str, Any]] = None) -> Any:
        """Call an MCP tool synchronously. Returns parsed JSON."""
        if self._closed:
            raise RuntimeError('MCP client is closed')
        if self._init_error is not None:
            raise RuntimeError(f'MCP client failed to initialize: {self._init_error}')
        if self._loop is None or self._session is None:
            raise RuntimeError('MCP client not initialized')

        with self._lock:
            fut = asyncio.run_coroutine_threadsafe(
                self._session.call_tool(tool_name, args or {}),
                self._loop,
            )
            result = fut.result(timeout=self._timeout_sec)

        text = None
        try:
            if getattr(result, 'isError', False):
                raise RuntimeError(f'MCP tool error: {result}')
            content = getattr(result, 'content', None) or []
            if content:
                text = getattr(content[0], 'text', None)
        except Exception:
            return result

        return _parse_json_maybe(text if isinstance(text, str) else '')

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._loop is not None:
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass


# ── Singleton helper ──────────────────────────────────────────────────────────

_CLIENTS: Dict[Tuple[str, Tuple[str, ...]], McpToolClient] = {}
_CLIENTS_LOCK = threading.Lock()

# Default server spec — points to our MCP server script
_SERVER_SCRIPT = str(Path(__file__).resolve().parent / 'server.py')
DEFAULT_SERVER = McpServerSpec(command=sys.executable, args=(_SERVER_SCRIPT,))


def get_mcp_client(
    *,
    server: Optional[McpServerSpec] = None,
    timeout_sec: float = 30.0,
) -> McpToolClient:
    """Return a singleton MCP client for the given server spec."""
    spec = server or DEFAULT_SERVER
    key  = (spec.command, tuple(spec.args))
    with _CLIENTS_LOCK:
        client = _CLIENTS.get(key)
        if client is None:
            client = McpToolClient(server=spec, timeout_sec=timeout_sec)
            _CLIENTS[key] = client
        return client


@atexit.register
def _close_all_clients() -> None:
    with _CLIENTS_LOCK:
        clients = list(_CLIENTS.values())
        _CLIENTS.clear()
    for c in clients:
        try:
            c.close()
        except Exception:
            pass
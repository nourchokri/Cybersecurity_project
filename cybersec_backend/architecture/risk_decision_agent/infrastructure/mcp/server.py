"""MCP server exposing CERT tools over the real Model Context Protocol (stdio).

This wraps implementations in `cert_tools/` and local JSON helpers.

When spawned as a subprocess by the Decision Agent, sys.path is augmented
so that absolute imports from the project root work correctly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Allow absolute imports from the Django project root when run as a subprocess.
_PROJECT_ROOT = str(Path(__file__).resolve().parents[4])  # cybersec_backend/
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from mcp.server.fastmcp import FastMCP

from architecture.risk_decision_agent.infrastructure.mcp.tools.cert_tools import CertTools

mcp = FastMCP("project_classe_cert_tools")

_CERT_TOOLS: Optional[CertTools] = None

# Resolve local_data path relative to this file.
_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "local_data"


def _json_text(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _get_cert_tools() -> CertTools:
    global _CERT_TOOLS
    if _CERT_TOOLS is None:
        _CERT_TOOLS = CertTools.from_env()
    return _CERT_TOOLS


@mcp.tool(name="cert.telemetry.get_file_metadata")
def cert_telemetry_get_file_metadata(file_id: str) -> str:
    tools = _get_cert_tools()
    return _json_text(tools.telemetry.get_file_metadata(file_id))


@mcp.tool(name="cert.identity.get_user_context")
def cert_identity_get_user_context(user_id: str, timestamp: str) -> str:
    tools = _get_cert_tools()
    return _json_text(tools.identity.get_user_context(user_id, timestamp))


@mcp.tool(name="cert.telemetry.get_user_summary")
def cert_telemetry_get_user_summary(user_id: str, start_ts: str, end_ts: str) -> str:
    tools = _get_cert_tools()
    return _json_text(tools.telemetry.get_user_summary(user_id, start_ts, end_ts))


@mcp.tool(name="cert.telemetry.get_user_baseline")
def cert_telemetry_get_user_baseline(user_id: str, as_of_ts: str, lookback_days: int = 30) -> str:
    tools = _get_cert_tools()
    return _json_text(tools.telemetry.get_user_baseline(user_id, as_of_ts, lookback_days=lookback_days))


@mcp.tool(name="cert.telemetry.get_deviations")
def cert_telemetry_get_deviations(
    user_id: str, start_ts: str, end_ts: str, baseline: Dict[str, Any],
) -> str:
    tools = _get_cert_tools()
    return _json_text(tools.telemetry.get_deviations(user_id, start_ts, end_ts, baseline))


@mcp.tool(name="cert.rule_library.explain")
def cert_rule_library_explain(rule_ids: List[str]) -> str:
    tools = _get_cert_tools()
    return _json_text(tools.rule_library.explain(rule_ids))


@mcp.tool(name="cert.policy.get_thresholds")
def cert_policy_get_thresholds() -> str:
    tools = _get_cert_tools()
    return _json_text(tools.policy.get_thresholds())


@mcp.tool(name="local_policy.get_thresholds")
def local_policy_get_thresholds(policy_path: Optional[str] = None) -> str:
    """Load thresholds from local JSON."""
    p = Path(policy_path) if policy_path else _DATA_DIR / "policy_db.json"
    thresholds = {"low_max": 0.4, "medium_max": 0.7}

    try:
        if p.exists():
            obj = json.loads(p.read_text(encoding="utf-8")) or {}
            thresholds["low_max"] = float(obj.get("low_max", thresholds["low_max"]))
            thresholds["medium_max"] = float(obj.get("medium_max", thresholds["medium_max"]))
    except Exception:
        pass

    return _json_text(thresholds)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

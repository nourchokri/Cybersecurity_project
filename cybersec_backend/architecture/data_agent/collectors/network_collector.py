"""
Network Collector — Captures active network connections.
Uses psutil to enumerate TCP/UDP connections with owning process.
"""

import psutil
import getpass
import socket
from datetime import datetime
from collectors.event_schema import StandardEvent, create_event


def get_process_name(pid: int) -> str:
    try:
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return "unknown"


def collect_network_connections() -> list[StandardEvent]:
    """Collect all current network connections with src/dst IPs and ports."""
    events = []
    user_id = getpass.getuser()
    device_id = socket.gethostname()
    now = datetime.now().isoformat()

    for conn in psutil.net_connections(kind="inet"):
        if not conn.raddr:
            continue

        src_ip = conn.laddr.ip if conn.laddr else "0.0.0.0"
        src_port = conn.laddr.port if conn.laddr else 0
        dst_ip = conn.raddr.ip
        dst_port = conn.raddr.port
        protocol = "TCP" if conn.type == socket.SOCK_STREAM else "UDP"
        proc_name = get_process_name(conn.pid) if conn.pid else "unknown"

        events.append(create_event(
            event_type="network_connection",
            event_category="network",
            action="connect",
            resource=f"{dst_ip}:{dst_port}",
            user_id=user_id,
            device_id=device_id,
            source="psutil",
            timestamp=now,
            src_ip=src_ip, dst_ip=dst_ip,
            src_port=src_port, dst_port=dst_port,
            protocol=protocol, process_name=proc_name,
        ))

    return events


if __name__ == "__main__":
    import json
    events = collect_network_connections()
    print(f"Collected {len(events)} network events")
    for e in events[:5]:
        print(json.dumps(e.model_dump(), indent=2))

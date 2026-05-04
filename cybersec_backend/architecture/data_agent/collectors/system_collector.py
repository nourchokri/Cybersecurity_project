"""
System Collector — Captures login/logout events, active user, idle time.
Uses psutil for system info and ctypes for Windows idle time detection.
"""

import psutil
import ctypes
import ctypes.wintypes
import platform
import getpass
import socket
from datetime import datetime
from collectors.event_schema import StandardEvent, create_event


def get_device_id() -> str:
    return socket.gethostname()


def get_user_id() -> str:
    return getpass.getuser()


def get_idle_time_seconds() -> float:
    """Get system idle time in seconds (Windows only)."""
    if platform.system() != "Windows":
        return 0.0

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.wintypes.UINT),
            ("dwTime", ctypes.wintypes.DWORD),
        ]

    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
    return millis / 1000.0


def get_boot_time() -> datetime:
    return datetime.fromtimestamp(psutil.boot_time())


def get_logged_in_users() -> list[dict]:
    users = []
    for user in psutil.users():
        users.append({
            "name": user.name,
            "terminal": user.terminal or "console",
            "host": user.host or "local",
            "started": datetime.fromtimestamp(user.started).isoformat(),
            "pid": user.pid,
        })
    return users


def collect_system_snapshot() -> list[StandardEvent]:
    """Collect a snapshot of current system state (sessions, idle time)."""
    events = []
    user_id = get_user_id()
    device_id = get_device_id()
    now = datetime.now().isoformat()
    idle_seconds = get_idle_time_seconds()
    boot_time = get_boot_time()
    session_duration = (datetime.now() - boot_time).total_seconds() / 60

    events.append(create_event(
        event_type="logon",
        event_category="system",
        action="active_session",
        resource=f"session://{user_id}@{device_id}",
        user_id=user_id,
        device_id=device_id,
        source="psutil",
        timestamp=now,
        idle_time_seconds=idle_seconds,
        session_duration_minutes=round(session_duration, 2),
    ))

    for user_info in get_logged_in_users():
        if user_info["name"] != user_id:
            events.append(create_event(
                event_type="logon",
                event_category="system",
                action="active_session",
                resource=f"session://{user_info['name']}@{device_id}",
                user_id=user_info["name"],
                device_id=device_id,
                source="psutil",
                timestamp=user_info["started"],
            ))

    return events


if __name__ == "__main__":
    import json
    events = collect_system_snapshot()
    for event in events:
        print(json.dumps(event.model_dump(), indent=2))

"""
Process Collector — Captures running processes and resource usage.
Detects suspicious processes (LOLBins commonly used in attacks).
"""

import psutil
import getpass
import socket
from datetime import datetime
from collectors.event_schema import StandardEvent, create_event

# Living off the Land Binaries — commonly abused in attacks
SUSPICIOUS_PROCESSES = {
    "powershell.exe", "pwsh.exe", "cmd.exe", "wscript.exe",
    "cscript.exe", "mshta.exe", "regsvr32.exe", "rundll32.exe",
    "certutil.exe", "bitsadmin.exe", "msiexec.exe", "wmic.exe",
    "python.exe", "python3.exe", "curl.exe", "wget.exe",
    "nmap.exe", "netcat.exe", "nc.exe", "psexec.exe",
}


def collect_running_processes(
    include_all: bool = False,
    cpu_threshold: float = 5.0,
    memory_threshold_mb: float = 100.0,
) -> list[StandardEvent]:
    """
    Collect running processes. By default only captures:
    - Suspicious processes (LOLBins)
    - High CPU (> threshold)
    - High memory (> threshold)
    Set include_all=True for everything.
    """
    events = []
    user_id = getpass.getuser()
    device_id = socket.gethostname()
    now = datetime.now().isoformat()

    for proc in psutil.process_iter(
        attrs=["pid", "name", "username", "cpu_percent",
               "memory_info", "ppid", "cmdline"]
    ):
        try:
            info = proc.info
            name = info.get("name", "unknown")
            cpu = info.get("cpu_percent", 0.0) or 0.0
            mem_info = info.get("memory_info")
            mem_mb = (mem_info.rss / (1024 * 1024)) if mem_info else 0.0
            pid = info.get("pid", 0)
            ppid = info.get("ppid", 0)
            cmdline = " ".join(info.get("cmdline") or [])
            proc_user = info.get("username", "")

            suspicious = name.lower() in SUSPICIOUS_PROCESSES
            high_cpu = cpu > cpu_threshold
            high_mem = mem_mb > memory_threshold_mb

            if not include_all and not (suspicious or high_cpu or high_mem):
                continue

            events.append(create_event(
                event_type="process_start",
                event_category="process",
                action="running",
                resource=name,
                user_id=proc_user or user_id,
                device_id=device_id,
                source="psutil",
                timestamp=now,
                pid=pid, parent_pid=ppid,
                cpu_percent=round(cpu, 2),
                memory_mb=round(mem_mb, 2),
                command_line=cmdline[:500],
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return events


if __name__ == "__main__":
    import json
    events = collect_running_processes()
    print(f"Collected {len(events)} process events")
    for e in events[:5]:
        print(json.dumps(e.model_dump(), indent=2))

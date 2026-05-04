"""
Windows Event Log Collector — Captures security events from Windows Event Log.
Tracks login failures, privilege escalation, service creation, process creation.
Critical for detecting authentication anomalies and privilege abuse (CERT r4.2).

Multi-log strategy:
  1. Try the Security log (requires Administrator privileges).
  2. Always read System + Application logs (no admin needed).
  3. Merge and deduplicate before returning.
"""

import getpass
import socket
from datetime import datetime, timedelta
from typing import Optional
from collectors.event_schema import StandardEvent, create_event

# Try to import win32evtlog for Windows Event Log access
try:
    import win32evtlog
    import win32evtlogutil
    import win32con
    EVTLOG_AVAILABLE = True
except ImportError:
    EVTLOG_AVAILABLE = False
    print("[windows_event_collector] win32evtlog not available. Install: pip install pywin32")


# ──────────────────────────────────────────────────────────────────────
# Event IDs we care about, organized by log source
# ──────────────────────────────────────────────────────────────────────

# Security log event IDs (need admin)
SECURITY_EVENT_IDS = {
    # Authentication
    4624: "Successful logon",
    4625: "Failed logon",
    4634: "Logoff",
    4648: "Logon using explicit credentials",
    4672: "Special privileges assigned (admin rights)",
    
    # Account Management
    4720: "User account created",
    4722: "User account enabled",
    4723: "Password change attempt",
    4724: "Password reset attempt",
    4725: "User account disabled",
    4726: "User account deleted",
    4738: "User account changed",
    4740: "User account locked out",
    4767: "User account unlocked",
    
    # Process/Service
    4688: "Process creation",
    4689: "Process termination",
    7045: "Service installed",
    7040: "Service start type changed",
    
    # Policy Changes
    4719: "System audit policy changed",
    4739: "Domain policy changed",
    
    # Scheduled Tasks
    4698: "Scheduled task created",
    4699: "Scheduled task deleted",
    4700: "Scheduled task enabled",
    4701: "Scheduled task disabled",
}

# System log event IDs (no admin needed — always accessible)
SYSTEM_EVENT_IDS = {
    # Service Control Manager
    7034: "Service crashed unexpectedly",
    7035: "Service sent start/stop control",
    7036: "Service entered running/stopped state",
    7040: "Service start type changed",
    7045: "New service installed",
    
    # DCOM / permissions
    10016: "DCOM permission error",
    
    # Windows Update
    19:   "Windows Update install success",
    20:   "Windows Update install failure",
    44:   "Windows Update download started",
    
    # Kernel / Boot
    1:    "System time changed / generic info",
    12:   "System startup",
    13:   "System shutdown",
    41:   "Unexpected shutdown (crash/power loss)",
    6005: "Event Log service started (boot)",
    6006: "Event Log service stopped (shutdown)",
    6008: "Unexpected shutdown",
    6009: "System boot information",
    
    # Disk / Storage
    7:    "Disk bad block",
    11:   "Disk controller reset",
    15:   "Disk not ready",
    
    # Network
    4227: "TCP/IP failed to establish connection",
}

# Application log event IDs (no admin needed)
APPLICATION_EVENT_IDS = {
    1000: "Application error",
    1001: "Windows Error Reporting",
    1002: "Application hang",
    1026: ".NET runtime error",
    11707: "Software install success",
    11708: "Software install failure",
    11724: "Software removal success",
}


def _mask_event_id(raw_id: int) -> int:
    """
    pywin32 returns EventID with qualifier bits in the high word.
    Mask with 0xFFFF to get the actual event ID.
    """
    return raw_id & 0xFFFF


def _read_log(
    log_name: str,
    target_event_ids: dict,
    hours_back: int,
    max_events: int,
    device_id: str,
    cutoff_time: datetime,
) -> list[StandardEvent]:
    """
    Read events from a single Windows Event Log channel.
    
    Returns a list of StandardEvent objects, or an empty list on failure.
    """
    events: list[StandardEvent] = []
    
    try:
        hand = win32evtlog.OpenEventLog(None, log_name)
    except Exception as e:
        print(f"[windows_event_collector] Cannot open {log_name} log: {e}")
        return events
    
    try:
        flags = (
            win32evtlog.EVENTLOG_BACKWARDS_READ
            | win32evtlog.EVENTLOG_SEQUENTIAL_READ
        )
        
        total = 0
        while total < max_events:
            event_records = win32evtlog.ReadEventLog(hand, flags, 0)
            if not event_records:
                break
            
            for event in event_records:
                if total >= max_events:
                    break
                
                # ── Mask the event ID ──
                eid = _mask_event_id(event.EventID)
                
                if eid not in target_event_ids:
                    continue
                
                # ── Time filter ──
                try:
                    event_time = datetime.fromtimestamp(
                        int(event.TimeGenerated.timestamp())
                    )
                    if event_time < cutoff_time:
                        # Events are in reverse chronological order → stop
                        total = max_events
                        break
                except Exception:
                    continue
                
                # ── Extract user ──
                user_id = getpass.getuser()
                if event.StringInserts and len(event.StringInserts) > 0:
                    for insert in event.StringInserts:
                        if insert and "\\" in insert:
                            user_id = insert.split("\\")[-1]
                            break
                        elif insert and "@" not in insert and insert.strip():
                            user_id = insert.strip()
                            break
                
                # ── Event description ──
                event_desc = target_event_ids.get(
                    eid, f"Event {eid}"
                )
                
                # ── Classify event ──
                event_type, event_category, action = _classify_event(
                    eid, log_name
                )
                
                # ── Metadata ──
                metadata = {
                    "event_id": eid,
                    "event_description": event_desc,
                    "log_source": log_name,
                }
                
                # For process creation events, extract command line
                if eid == 4688 and event.StringInserts and len(event.StringInserts) > 5:
                    try:
                        process_name = (
                            event.StringInserts[5]
                            if len(event.StringInserts) > 5
                            else ""
                        )
                        command_line = (
                            event.StringInserts[8]
                            if len(event.StringInserts) > 8
                            else ""
                        )
                        metadata["process_name"] = process_name
                        metadata["command_line"] = command_line[:500]
                    except Exception:
                        pass
                
                events.append(
                    create_event(
                        event_type=event_type,
                        event_category=event_category,
                        action=action,
                        resource=f"event_{eid}",
                        user_id=user_id,
                        device_id=device_id,
                        source=f"windows_{log_name.lower()}_log",
                        timestamp=event_time.isoformat(),
                        **metadata,
                    )
                )
                total += 1
    
    finally:
        win32evtlog.CloseEventLog(hand)
    
    print(
        f"[windows_event_collector] {log_name} log: "
        f"collected {len(events)} events"
    )
    return events


def _classify_event(eid: int, log_name: str):
    """
    Return (event_type, event_category, action) for a given event ID.
    
    IMPORTANT: event_type must be one of the StandardEvent Literal values:
      logon, logoff, file_access, device_connect, device_disconnect,
      process_start, process_stop, network_connection, http_request,
      email_sent, email_received
    
    event_category must be one of:
      system, file, device, process, network, web, email
    """
    
    # --- Security log: Authentication ---
    if eid in (4624, 4648):
        return "logon", "system", "login_success"
    if eid == 4625:
        return "logon", "system", "login_failed"
    if eid == 4634:
        return "logoff", "system", "logout"
    if eid == 4672:
        return "logon", "system", "privilege_escalation"
    
    # --- Security log: Process / Service ---
    if eid == 4688:
        return "process_start", "process", "create"
    if eid == 4689:
        return "process_stop", "process", "terminate"
    if eid == 7045:
        return "process_start", "process", "service_install"
    if eid in (4698, 4699, 4700, 4701):
        return "process_start", "process", "scheduled_task"
    
    # --- Security log: Account Management → map to logon (closest match) ---
    if eid in (4720, 4722, 4723, 4724, 4725, 4726, 4738, 4740, 4767):
        return "logon", "system", "account_management"
    
    # --- Security log: Policy Changes → map to logon/system ---
    if eid in (4719, 4739):
        return "logon", "system", "policy_change"
    
    # --- System log: Service events → process_start / process_stop ---
    if eid in (7034, 7035, 7036, 7040):
        return "process_start", "process", "service_state_change"
    if eid == 7045:
        return "process_start", "process", "service_install"
    if eid == 10016:
        return "process_start", "system", "dcom_error"
    
    # --- System log: Boot / Shutdown ---
    if eid in (12, 6005, 6009, 1):
        return "logon", "system", "system_startup"
    if eid in (13, 6006):
        return "logoff", "system", "system_shutdown"
    if eid in (41, 6008):
        return "logoff", "system", "unexpected_shutdown"
    
    # --- System log: Updates ---
    if eid in (19, 20, 44):
        return "process_start", "system", "windows_update"
    
    # --- System log: Disk / Hardware ---
    if eid in (7, 11, 15):
        return "device_connect", "device", "disk_error"
    
    # --- System log: Network ---
    if eid == 4227:
        return "network_connection", "network", "connection_failed"
    
    # --- Application log: Errors → process_stop ---
    if eid in (1000, 1002, 1026):
        return "process_stop", "process", "app_crash"
    if eid == 1001:
        return "process_stop", "process", "error_reporting"
    
    # --- Application log: Software install → process_start ---
    if eid in (11707, 11708, 11724):
        return "process_start", "process", "software_install"
    
    # Fallback — use logon/system as safest default
    return "logon", "system", f"{log_name.lower()}_event"


def collect_windows_events(
    hours_back: int = 24,
    max_events: int = 1000,
    event_ids: Optional[list[int]] = None
) -> list[StandardEvent]:
    """
    Collect security-relevant events from Windows Event Logs.
    
    Strategy:
      1. Try the Security log (requires admin). If access is denied, skip gracefully.
      2. Always read System and Application logs (accessible without admin).
      3. Return the merged result.
    
    This ensures we always return *something* useful, even without elevation.
    """
    if not EVTLOG_AVAILABLE:
        print("[windows_event_collector] Windows Event Log access not available (pywin32 not installed)")
        return []
    
    device_id = socket.gethostname()
    cutoff_time = datetime.now() - timedelta(hours=hours_back)
    all_events: list[StandardEvent] = []
    
    # ── 1. Security log (admin required) ──
    security_ids = dict(SECURITY_EVENT_IDS)
    if event_ids is not None:
        # If caller specified specific IDs, filter Security IDs to those
        security_ids = {k: v for k, v in security_ids.items() if k in event_ids}
    
    security_events = _read_log(
        log_name="Security",
        target_event_ids=security_ids,
        hours_back=hours_back,
        max_events=max_events,
        device_id=device_id,
        cutoff_time=cutoff_time,
    )
    all_events.extend(security_events)
    
    # ── 2. System log (always accessible) ──
    remaining = max(0, max_events - len(all_events))
    if remaining > 0:
        system_events = _read_log(
            log_name="System",
            target_event_ids=SYSTEM_EVENT_IDS,
            hours_back=hours_back,
            max_events=remaining,
            device_id=device_id,
            cutoff_time=cutoff_time,
        )
        all_events.extend(system_events)
    
    # ── 3. Application log (always accessible) ──
    remaining = max(0, max_events - len(all_events))
    if remaining > 0:
        app_events = _read_log(
            log_name="Application",
            target_event_ids=APPLICATION_EVENT_IDS,
            hours_back=hours_back,
            max_events=remaining,
            device_id=device_id,
            cutoff_time=cutoff_time,
        )
        all_events.extend(app_events)
    
    # ── Summary ──
    source_breakdown = {}
    for evt in all_events:
        src = "unknown"
        if hasattr(evt, 'source'):
            src = evt.source
        elif isinstance(evt, dict):
            src = evt.get('source', 'unknown')
        source_breakdown[src] = source_breakdown.get(src, 0) + 1
    
    print(
        f"[windows_event_collector] Total: {len(all_events)} events "
        f"(breakdown: {source_breakdown})"
    )
    
    if not all_events:
        print(
            "[windows_event_collector] WARNING: 0 events collected. "
            "Possible causes:\n"
            "  • Security log requires Administrator privileges\n"
            "  • No matching events in the requested time window "
            f"(hours_back={hours_back})\n"
            "  • Try increasing hours_back or running as Administrator"
        )
    
    return all_events


if __name__ == "__main__":
    import json
    print("Collecting Windows security events...")
    print("Note: Run as Administrator for full Security log access\n")
    events = collect_windows_events(hours_back=24)
    print(f"\nCollected {len(events)} events")
    for e in events[:5]:
        print(json.dumps(e.model_dump(), indent=2))

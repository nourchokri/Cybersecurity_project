"""
Registry Collector — Monitors Windows Registry for persistence mechanisms.
Tracks changes to Run keys, startup folders, services, scheduled tasks.
Critical for detecting malware persistence and privilege escalation (CERT r4.2).
"""

import getpass
import socket
from datetime import datetime
from typing import Optional
from collectors.event_schema import StandardEvent, create_event

# Try to import winreg for Windows Registry access
try:
    import winreg
    REGISTRY_AVAILABLE = True
except ImportError:
    REGISTRY_AVAILABLE = False
    print("[registry_collector] winreg not available (should be built-in on Windows)")


# Critical registry keys for persistence detection
PERSISTENCE_KEYS = [
    # Auto-run keys (most common persistence mechanism)
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKLM_Run"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce", "HKLM_RunOnce"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKCU_Run"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce", "HKCU_RunOnce"),
    
    # Startup folders (legacy but still used)
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders", "Shell_Folders"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders", "User_Shell_Folders"),
    
    # Services (can be used for persistence)
    (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services", "Services"),
    
    # Winlogon (session hijacking)
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon", "Winlogon"),
    
    # Image File Execution Options (debugger hijacking)
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options", "IFEO"),
]


def read_registry_key_values(hkey, path: str) -> dict:
    """Read all values from a registry key."""
    values = {}
    try:
        key = winreg.OpenKey(hkey, path, 0, winreg.KEY_READ)
        i = 0
        while True:
            try:
                name, value, value_type = winreg.EnumValue(key, i)
                values[name or "(Default)"] = str(value)
                i += 1
            except OSError:
                break
        winreg.CloseKey(key)
    except FileNotFoundError:
        pass
    except PermissionError:
        pass
    return values


def collect_persistence_mechanisms() -> list[StandardEvent]:
    """
    Collect current persistence mechanisms from registry.
    Snapshots Run keys, services, and other auto-start locations.
    """
    if not REGISTRY_AVAILABLE:
        print("[registry_collector] Registry access not available")
        return []
    
    events = []
    user_id = getpass.getuser()
    device_id = socket.gethostname()
    now = datetime.now().isoformat()
    
    for hkey, path, key_name in PERSISTENCE_KEYS:
        values = read_registry_key_values(hkey, path)
        
        for value_name, value_data in values.items():
            # Skip empty or system values
            if not value_data or value_data == "":
                continue
            
            # Determine sensitivity based on key location
            sensitivity = 1  # Medium by default
            if "Run" in key_name:
                sensitivity = 2  # High - direct auto-run
            elif "Services" in key_name:
                sensitivity = 1  # Medium - services are common
            elif "Winlogon" in key_name or "IFEO" in key_name:
                sensitivity = 3  # Critical - advanced techniques
            
            events.append(create_event(
                event_type="process_start",
                event_category="process",
                action="registry_persistence",
                resource=f"{key_name}\\{value_name}",
                user_id=user_id,
                device_id=device_id,
                source="registry_monitor",
                timestamp=now,
                registry_key=key_name,
                registry_value_name=value_name,
                registry_value_data=value_data[:500],  # Truncate long paths
                sensitivity_level=sensitivity,
            ))
    
    print(f"[registry_collector] Found {len(events)} persistence mechanisms")
    return events


def detect_suspicious_registry_entries(events: list[StandardEvent]) -> list[StandardEvent]:
    """
    Analyze registry entries for suspicious patterns.
    Flags entries with suspicious characteristics.
    """
    suspicious_patterns = [
        "powershell", "cmd.exe", "wscript", "cscript", "mshta",
        "regsvr32", "rundll32", "certutil", "bitsadmin",
        "temp", "appdata", "programdata", "public",
        ".vbs", ".js", ".bat", ".ps1", ".hta",
    ]
    
    for event in events:
        value_data = event.metadata.registry_value_data or ""
        value_data_lower = value_data.lower()
        
        # Check for suspicious patterns
        found_patterns = [p for p in suspicious_patterns if p in value_data_lower]
        
        if found_patterns:
            # Mark as suspicious
            event.metadata.is_suspicious = True
            event.metadata.suspicious_indicators = ",".join(found_patterns)
            event.metadata.sensitivity_level = 3  # Elevate to critical
    
    return events


if __name__ == "__main__":
    import json
    print("Collecting registry persistence mechanisms...")
    print("Note: Run as Administrator for full access\n")
    
    events = collect_persistence_mechanisms()
    events = detect_suspicious_registry_entries(events)
    
    print(f"\nCollected {len(events)} registry entries")
    
    # Show suspicious ones first
    suspicious = [e for e in events if getattr(e.metadata, 'is_suspicious', False)]
    if suspicious:
        print(f"\n⚠️  Found {len(suspicious)} suspicious entries:")
        for e in suspicious[:5]:
            print(json.dumps(e.model_dump(), indent=2))
    else:
        print("\nSample entries:")
        for e in events[:5]:
            print(json.dumps(e.model_dump(), indent=2))

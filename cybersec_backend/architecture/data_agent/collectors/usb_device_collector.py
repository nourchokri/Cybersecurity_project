"""
USB Device Collector — Captures complete USB device history from Windows Registry.
Tracks all USB devices ever connected, even if no longer present.
Critical for detecting data exfiltration via removable media (CERT r4.2).
"""

import os
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
    print("[usb_device_collector] winreg not available (should be built-in on Windows)")


def parse_device_info(device_key_name: str) -> dict:
    """Parse USB device key name to extract vendor, product, serial."""
    # Format: Disk&Ven_SanDisk&Prod_Cruzer_Glide&Rev_1.00
    # or: USB\VID_0781&PID_5567\4C530001234567890123
    parts = {}
    
    if "&Ven_" in device_key_name:
        try:
            ven_start = device_key_name.index("&Ven_") + 5
            ven_end = device_key_name.index("&", ven_start) if "&" in device_key_name[ven_start:] else len(device_key_name)
            parts["vendor"] = device_key_name[ven_start:ven_end].replace("_", " ")
        except Exception:
            pass
    
    if "&Prod_" in device_key_name:
        try:
            prod_start = device_key_name.index("&Prod_") + 6
            prod_end = device_key_name.index("&", prod_start) if "&" in device_key_name[prod_start:] else len(device_key_name)
            parts["product"] = device_key_name[prod_start:prod_end].replace("_", " ")
        except Exception:
            pass
    
    if "VID_" in device_key_name:
        try:
            vid_start = device_key_name.index("VID_") + 4
            parts["vendor_id"] = device_key_name[vid_start:vid_start+4]
        except Exception:
            pass
    
    if "PID_" in device_key_name:
        try:
            pid_start = device_key_name.index("PID_") + 4
            parts["product_id"] = device_key_name[pid_start:pid_start+4]
        except Exception:
            pass
    
    # Serial number is usually after the last backslash
    if "\\" in device_key_name:
        parts["serial"] = device_key_name.split("\\")[-1]
    
    return parts


def collect_usb_device_history() -> list[StandardEvent]:
    """
    Collect USB device history from Windows Registry.
    Reads USBSTOR registry key which contains all USB storage devices ever connected.
    """
    if not REGISTRY_AVAILABLE:
        print("[usb_device_collector] Registry access not available")
        return []
    
    events = []
    user_id = getpass.getuser()
    device_id = socket.gethostname()
    now = datetime.now().isoformat()
    
    # Registry paths to check
    registry_paths = [
        # USB Storage devices
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Enum\USBSTOR"),
        # USB devices (more detailed)
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Enum\USB"),
    ]
    
    seen_devices = set()
    
    for hkey, path in registry_paths:
        try:
            key = winreg.OpenKey(hkey, path, 0, winreg.KEY_READ)
            
            # Enumerate all subkeys (each is a device type)
            i = 0
            while True:
                try:
                    device_type = winreg.EnumKey(key, i)
                    i += 1
                    
                    # Open device type key
                    device_type_key = winreg.OpenKey(key, device_type, 0, winreg.KEY_READ)
                    
                    # Enumerate all instances of this device type
                    j = 0
                    while True:
                        try:
                            instance_id = winreg.EnumKey(device_type_key, j)
                            j += 1
                            
                            # Create unique identifier
                            device_uid = f"{device_type}\\{instance_id}"
                            if device_uid in seen_devices:
                                continue
                            seen_devices.add(device_uid)
                            
                            # Open instance key to read properties
                            instance_key = winreg.OpenKey(device_type_key, instance_id, 0, winreg.KEY_READ)
                            
                            # Read device properties
                            friendly_name = ""
                            device_desc = ""
                            first_install = None
                            last_arrival = None
                            
                            try:
                                friendly_name, _ = winreg.QueryValueEx(instance_key, "FriendlyName")
                            except FileNotFoundError:
                                pass
                            
                            try:
                                device_desc, _ = winreg.QueryValueEx(instance_key, "DeviceDesc")
                                # Remove @oem prefix if present
                                if device_desc.startswith("@"):
                                    device_desc = device_desc.split(";")[-1] if ";" in device_desc else device_desc
                            except FileNotFoundError:
                                pass
                            
                            # Try to get timestamps (stored as binary data)
                            # Note: These are not always available
                            
                            # Parse device info from key name
                            device_info = parse_device_info(device_uid)
                            
                            # Create event
                            events.append(create_event(
                                event_type="device_connect",
                                event_category="device",
                                action="usb_history",
                                resource=friendly_name or device_desc or device_uid,
                                user_id=user_id,
                                device_id=device_id,
                                source="registry_usbstor",
                                timestamp=now,
                                device_type="usb_storage",
                                device_vendor=device_info.get("vendor", ""),
                                device_product=device_info.get("product", ""),
                                device_serial=device_info.get("serial", ""),
                                device_vid=device_info.get("vendor_id", ""),
                                device_pid=device_info.get("product_id", ""),
                                device_description=device_desc,
                            ))
                            
                            winreg.CloseKey(instance_key)
                            
                        except OSError:
                            # No more instances
                            break
                    
                    winreg.CloseKey(device_type_key)
                    
                except OSError:
                    # No more device types
                    break
            
            winreg.CloseKey(key)
            
        except FileNotFoundError:
            print(f"[usb_device_collector] Registry path not found: {path}")
        except PermissionError:
            print(f"[usb_device_collector] Permission denied for: {path}")
            print("  Note: Administrator privileges may be required")
        except Exception as e:
            print(f"[usb_device_collector] Error reading registry: {e}")
    
    print(f"[usb_device_collector] Found {len(events)} USB devices in history")
    return events


def collect_currently_connected_usb() -> list[StandardEvent]:
    """
    Collect currently connected USB devices using WMI.
    Requires pywin32 or wmi module.
    """
    events = []
    user_id = getpass.getuser()
    device_id = socket.gethostname()
    now = datetime.now().isoformat()
    
    try:
        import wmi
        c = wmi.WMI()
        
        # Query USB devices
        for usb in c.Win32_USBHub():
            events.append(create_event(
                event_type="device_connect",
                event_category="device",
                action="usb_connected",
                resource=usb.Name or usb.DeviceID,
                user_id=user_id,
                device_id=device_id,
                source="wmi",
                timestamp=now,
                device_type="usb_hub",
                device_description=usb.Description or "",
                device_status=usb.Status or "",
            ))
        
        print(f"[usb_device_collector] Found {len(events)} currently connected USB devices")
        
    except ImportError:
        print("[usb_device_collector] WMI module not available. Install: pip install wmi")
    except Exception as e:
        print(f"[usb_device_collector] Error querying WMI: {e}")
    
    return events


if __name__ == "__main__":
    import json
    print("Collecting USB device history from Registry...")
    print("Note: Run as Administrator for full access\n")
    
    events = collect_usb_device_history()
    print(f"\nCollected {len(events)} USB device history records")
    
    for e in events[:5]:
        print(json.dumps(e.model_dump(), indent=2))
    
    print("\n" + "="*60)
    print("Collecting currently connected USB devices...")
    current = collect_currently_connected_usb()
    print(f"Found {len(current)} currently connected devices")

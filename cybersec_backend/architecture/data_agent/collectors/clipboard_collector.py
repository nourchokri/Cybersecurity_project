"""
Clipboard Collector — Monitors clipboard activity for sensitive data patterns.
Detects potential data staging behavior (copying sensitive info before exfiltration).
Critical for insider threat detection (CERT r4.2).
"""

import re
import time
import getpass
import socket
from datetime import datetime
from typing import Optional
from collectors.event_schema import StandardEvent, create_event

# Try to import clipboard libraries
try:
    import win32clipboard
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False
    print("[clipboard_collector] win32clipboard not available. Install: pip install pywin32")


# Sensitive data patterns
SENSITIVE_PATTERNS = {
    "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "api_key": r"\b[A-Za-z0-9]{32,}\b",
    "password_field": r"(password|passwd|pwd)[\s:=]+\S+",
    "private_key": r"-----BEGIN (RSA |)PRIVATE KEY-----",
    "aws_key": r"AKIA[0-9A-Z]{16}",
    "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
}


def classify_clipboard_content(text: str) -> dict:
    """Analyze clipboard content and detect sensitive patterns."""
    if not text or len(text) < 3:
        return {"sensitivity": 0, "patterns": []}
    
    detected_patterns = []
    max_sensitivity = 0
    
    for pattern_name, pattern_regex in SENSITIVE_PATTERNS.items():
        if re.search(pattern_regex, text, re.IGNORECASE):
            detected_patterns.append(pattern_name)
            # Assign sensitivity levels
            if pattern_name in ["credit_card", "ssn", "private_key", "aws_key"]:
                max_sensitivity = max(max_sensitivity, 3)  # Critical
            elif pattern_name in ["password_field", "api_key"]:
                max_sensitivity = max(max_sensitivity, 2)  # High
            else:
                max_sensitivity = max(max_sensitivity, 1)  # Medium
    
    # Check for large text blocks (potential data staging)
    if len(text) > 1000:
        detected_patterns.append("large_text_block")
        max_sensitivity = max(max_sensitivity, 1)
    
    return {
        "sensitivity": max_sensitivity,
        "patterns": detected_patterns,
        "length": len(text),
    }


def get_clipboard_text() -> Optional[str]:
    """Get current clipboard text content."""
    if not CLIPBOARD_AVAILABLE:
        return None
    
    try:
        win32clipboard.OpenClipboard()
        try:
            text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            return text
        except TypeError:
            # Clipboard doesn't contain text
            return None
        finally:
            win32clipboard.CloseClipboard()
    except Exception:
        return None


def monitor_clipboard(duration_seconds: int = 60, check_interval: float = 1.0) -> list[StandardEvent]:
    """
    Monitor clipboard for changes over a duration.
    Records each unique clipboard change with sensitivity analysis.
    """
    if not CLIPBOARD_AVAILABLE:
        print("[clipboard_collector] Clipboard monitoring not available (pywin32 not installed)")
        return []
    
    events = []
    user_id = getpass.getuser()
    device_id = socket.gethostname()
    
    last_content = None
    start_time = time.time()
    
    print(f"[clipboard_collector] Monitoring clipboard for {duration_seconds} seconds...")
    
    while time.time() - start_time < duration_seconds:
        current_content = get_clipboard_text()
        
        # Check if clipboard changed
        if current_content and current_content != last_content:
            analysis = classify_clipboard_content(current_content)
            
            # Only record if there's something interesting
            if analysis["sensitivity"] > 0 or analysis["length"] > 100:
                # Truncate content for privacy (store hash or length, not full content)
                content_preview = current_content[:100] if len(current_content) > 100 else current_content
                
                events.append(create_event(
                    event_type="file_access",  # Closest match in schema
                    event_category="file",
                    action="clipboard_copy",
                    resource=f"clipboard_{analysis['length']}_chars",
                    user_id=user_id,
                    device_id=device_id,
                    source="clipboard_monitor",
                    clipboard_length=analysis["length"],
                    clipboard_sensitivity=analysis["sensitivity"],
                    clipboard_patterns=",".join(analysis["patterns"]),
                    clipboard_preview=content_preview,
                ))
                
                print(f"  Clipboard change detected: {analysis['length']} chars, "
                      f"sensitivity={analysis['sensitivity']}, patterns={analysis['patterns']}")
            
            last_content = current_content
        
        time.sleep(check_interval)
    
    print(f"[clipboard_collector] Captured {len(events)} clipboard events")
    return events


if __name__ == "__main__":
    import json
    print("Monitoring clipboard for 30 seconds...")
    print("Try copying some text to test!\n")
    events = monitor_clipboard(duration_seconds=30)
    print(f"\nCollected {len(events)} clipboard events")
    for e in events:
        print(json.dumps(e.model_dump(), indent=2))

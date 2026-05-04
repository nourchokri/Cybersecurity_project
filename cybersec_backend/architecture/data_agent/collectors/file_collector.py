"""
File Collector — Monitors file system events in real-time.
Uses watchdog for live monitoring and os.walk for snapshots.
Detects USB drives and classifies file sensitivity.
"""

import os
import string
import platform
import getpass
import socket
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from collectors.event_schema import StandardEvent, create_event

# Sensitivity classification
HIGH_SENS_EXT = {".pem", ".key", ".pfx", ".env", ".sql", ".bak", ".db", ".sqlite"}
MED_SENS_EXT = {".xlsx", ".docx", ".pdf", ".csv", ".pptx", ".json", ".xml"}
SENS_PATHS = ["financial", "hr", "confidential", "secret", "private", "credentials"]


def infer_sensitivity(file_path: str) -> int:
    """0=low, 1=medium, 2=high."""
    ext = Path(file_path).suffix.lower()
    path_lower = file_path.lower()
    if ext in HIGH_SENS_EXT or any(s in path_lower for s in SENS_PATHS):
        return 2
    if ext in MED_SENS_EXT:
        return 1
    return 0


def is_usb_path(file_path: str) -> bool:
    """Check if path is on a removable drive (Windows)."""
    if platform.system() != "Windows":
        return False
    try:
        import ctypes
        drive = os.path.splitdrive(file_path)[0] + "\\"
        return ctypes.windll.kernel32.GetDriveTypeW(drive) == 2
    except Exception:
        return False


class SecurityFileHandler(FileSystemEventHandler):
    """Converts watchdog events into StandardEvents and persists to log file."""

    LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "logs", "file_events.jsonl")

    def __init__(self, user_id: str, device_id: str):
        super().__init__()
        self.user_id = user_id
        self.device_id = device_id
        self.collected_events: list[StandardEvent] = []
        # Ensure log directory exists
        os.makedirs(os.path.dirname(self.LOG_FILE), exist_ok=True)
        # Load any previously saved events
        self._load_existing_events()

    def _load_existing_events(self):
        """Load events from previous sessions."""
        import json
        if not os.path.exists(self.LOG_FILE):
            return
        try:
            with open(self.LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        self.collected_events.append(StandardEvent(**data))
        except Exception:
            pass  # If log is corrupted, start fresh

    def _save_event(self, event: StandardEvent):
        """Append a single event to the log file."""
        import json
        with open(self.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.model_dump()) + "\n")

    # Only ignore files that are guaranteed noise or cause feedback loops
    IGNORE_PATTERNS = {"__pycache__", ".pyc", ".jsonl", "file_events",
                       ".git", ".venv", "node_modules"}

    def _should_ignore(self, path: str) -> bool:
        """Filter out our own files to prevent feedback loops."""
        path_lower = path.lower()
        return any(p in path_lower for p in self.IGNORE_PATTERNS)

    def _make_event(self, action: str, file_path: str):
        if self._should_ignore(file_path):
            return
        event = create_event(
            event_type="file_access", event_category="file",
            action=action, resource=file_path,
            user_id=self.user_id, device_id=self.device_id,
            source="watchdog",
            file_path=file_path,
            file_extension=Path(file_path).suffix.lower(),
            file_size_bytes=os.path.getsize(file_path) if os.path.exists(file_path) else None,
            is_usb=is_usb_path(file_path),
            sensitivity_level=infer_sensitivity(file_path),
        )
        self.collected_events.append(event)
        self._save_event(event)

    def on_created(self, event):
        if not event.is_directory:
            self._make_event("create", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._make_event("delete", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._make_event("modify", event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._make_event("move", event.dest_path)


def start_file_monitor(watch_paths: list[str], duration_seconds: int = 60) -> list[StandardEvent]:
    """Monitor file system events on given paths for a duration."""
    import time
    user_id = getpass.getuser()
    device_id = socket.gethostname()
    handler = SecurityFileHandler(user_id, device_id)
    observer = Observer()
    for path in watch_paths:
        if os.path.isdir(path):
            observer.schedule(handler, path, recursive=True)
    observer.start()
    try:
        time.sleep(duration_seconds)
    finally:
        observer.stop()
        observer.join()
    return handler.collected_events


def collect_file_snapshot(scan_dirs: Optional[list[str]] = None) -> list[StandardEvent]:
    """Snapshot of files modified in the last hour."""
    if scan_dirs is None:
        scan_dirs = [os.path.expanduser("~")]
    events = []
    user_id = getpass.getuser()
    device_id = socket.gethostname()
    one_hour_ago = datetime.now() - timedelta(hours=1)

    for scan_dir in scan_dirs:
        if not os.path.isdir(scan_dir):
            continue
        for root, dirs, files in os.walk(scan_dir):
            if root.replace(scan_dir, "").count(os.sep) > 3:
                dirs.clear()
                continue
            for filename in files:
                filepath = os.path.join(root, filename)
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if mtime > one_hour_ago:
                        events.append(create_event(
                            event_type="file_access", event_category="file",
                            action="modify", resource=filepath,
                            user_id=user_id, device_id=device_id,
                            source="os_scan", timestamp=mtime.isoformat(),
                            file_path=filepath,
                            file_extension=Path(filepath).suffix.lower(),
                            file_size_bytes=os.path.getsize(filepath),
                            is_usb=is_usb_path(filepath),
                            sensitivity_level=infer_sensitivity(filepath),
                        ))
                except (OSError, PermissionError):
                    continue
    return events


if __name__ == "__main__":
    import json
    events = collect_file_snapshot()
    print(f"Collected {len(events)} file events")
    for e in events[:5]:
        print(json.dumps(e.model_dump(), indent=2))

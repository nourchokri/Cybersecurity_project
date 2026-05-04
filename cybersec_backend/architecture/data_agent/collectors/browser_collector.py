"""
Browser Collector — Captures browser history from Chrome and Edge.
Reads SQLite history databases (copies to temp to avoid lock conflicts).

Fix: browser attribution is now derived from the actual DB path, not a
     loop variable, so Chrome visits can never be labelled as Edge events.
"""

import os
import shutil
import sqlite3
import tempfile
import getpass
import socket
from datetime import datetime, timedelta
from urllib.parse import urlparse
from typing import Optional
from collectors.event_schema import StandardEvent, create_event

SUSPICIOUS_DOMAINS = {
    "mega.nz", "mediafire.com", "anonfiles.com", "gofile.io",
    "transfer.sh", "file.io",        # File sharing / exfil
    "torproject.org", "tails.boum.org",  # Anonymization
    "pastebin.com", "ghostbin.com",     # Data dumps
    "exploit-db.com", "0day.today",     # Hacking
    "indeed.com", "glassdoor.com",      # Job search (insider threat indicator)
}

# ── Canonical base paths ──────────────────────────────────────────────────────
def _browser_base(browser: str) -> str:
    """Return the canonical User Data directory for the given browser."""
    local = os.environ.get("LOCALAPPDATA", "")
    if browser == "chrome":
        return os.path.join(local, "Google", "Chrome", "User Data")
    elif browser == "edge":
        return os.path.join(local, "Microsoft", "Edge", "User Data")
    raise ValueError(f"Unknown browser: {browser!r}")


def get_browser_history_paths(browser: str) -> list[tuple[str, str]]:
    """
    Return a list of (profile_name, history_path) for all profiles that
    have a History file.  browser must be 'chrome' or 'edge'.

    Fix: uses a single resolved base per browser so paths can never
    cross-contaminate between browsers.
    """
    base = _browser_base(browser)
    if not os.path.isdir(base):
        return []

    # Resolve to a real path so symlinks don't create duplicates
    base = os.path.realpath(base)

    results = []
    candidates = ["Default"] + [f"Profile {i}" for i in range(1, 10)]
    for profile in candidates:
        path = os.path.join(base, profile, "History")
        if os.path.exists(path):
            results.append((profile, path))
    return results


def _infer_browser_from_path(db_path: str) -> str:
    """
    Derive the browser name from the actual file-system path of the DB.
    This is the authoritative source — never trust the caller's label alone.
    """
    real = os.path.realpath(db_path).replace("\\", "/").lower()
    if "google/chrome" in real or "google\\chrome" in real.replace("/", "\\"):
        return "chrome"
    if "microsoft/edge" in real or "microsoft\\edge" in real.replace("/", "\\"):
        return "edge"
    # Fallback: keep whatever the caller said (logged as a warning)
    return "unknown"


def extract_history_from_db(
    db_path: str,
    hours_back: int = 24,
    browser_name: str = "chrome",
) -> list[StandardEvent]:
    """
    Extract browsing history from a Chromium SQLite DB.

    Fix: browser_name is cross-checked against the real path of db_path.
    If they disagree the path-derived value wins, and a warning is printed.
    """
    # ── Authoritative browser label ──────────────────────────────────────────
    inferred = _infer_browser_from_path(db_path)
    if inferred != "unknown" and inferred != browser_name:
        print(
            f"[browser_collector] WARNING: caller passed browser_name="
            f"{browser_name!r} but path resolves to {inferred!r}. "
            f"Using path-derived value."
        )
        browser_name = inferred

    events: list[StandardEvent] = []
    user_id = getpass.getuser()
    device_id = socket.gethostname()
    temp_dir = tempfile.mkdtemp()
    temp_db = os.path.join(temp_dir, "History_copy")

    try:
        shutil.copy2(db_path, temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Chrome timestamps: microseconds since 1601-01-01
        chrome_epoch_offset = 11644473600
        cutoff_unix = (datetime.now() - timedelta(hours=hours_back)).timestamp()
        cutoff_chrome = int((cutoff_unix + chrome_epoch_offset) * 1_000_000)

        cursor.execute(
            """
            SELECT url, title, visit_count, last_visit_time
            FROM urls
            WHERE last_visit_time > ?
            ORDER BY last_visit_time DESC
            LIMIT 500
            """,
            (cutoff_chrome,),
        )

        for url, title, visit_count, last_visit_time in cursor.fetchall():
            unix_ts = (last_visit_time / 1_000_000) - chrome_epoch_offset
            try:
                ts = datetime.fromtimestamp(unix_ts).isoformat()
            except (OSError, ValueError):
                ts = datetime.now().isoformat()

            domain = urlparse(url).netloc
            events.append(
                create_event(
                    event_type="http_request",
                    event_category="web",
                    action="visit",
                    resource=url,
                    user_id=user_id,
                    device_id=device_id,
                    source=f"browser_{browser_name}",  # now always correct
                    timestamp=ts,
                    url=url,
                    domain=domain,
                    page_title=title or "",
                    visit_count=visit_count,
                )
            )
        conn.close()

    except Exception as e:
        print(f"[browser_collector] Error reading {browser_name} history "
              f"({db_path}): {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return events


def collect_browser_history(hours_back: int = 24) -> list[StandardEvent]:
    """
    Collect browser history from ALL Chrome and Edge profiles.

    Fix: paths for each browser are fully resolved before iteration so
    there is zero chance of cross-browser profile aliasing.
    """
    all_events: list[StandardEvent] = []
    seen_paths: set[str] = set()          # guard against symlink duplicates

    for browser in ("chrome", "edge"):
        profiles = get_browser_history_paths(browser)
        print(
            f"[browser_collector] {browser} profiles found: "
            f"{[p for p, _ in profiles] if profiles else 'NONE'}"
        )
        for profile_name, db_path in profiles:
            real_path = os.path.realpath(db_path)
            if real_path in seen_paths:
                print(f"  → {browser}/{profile_name}: SKIPPED (duplicate path)")
                continue
            seen_paths.add(real_path)

            events = extract_history_from_db(db_path, hours_back, browser)
            print(f"  → {browser}/{profile_name}: {len(events)} events")
            all_events.extend(events)

    return all_events


if __name__ == "__main__":
    import json
    events = collect_browser_history(hours_back=48)
    print(f"\nCollected {len(events)} browser events")
    for e in events[:5]:
        print(json.dumps(e.model_dump(), indent=2))
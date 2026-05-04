"""
Session Aggregator - Transforms StandardEvent objects into SessionInput format.

This module bridges the gap between Data Agent's event collection and
Behavior Agent's session-based analysis.
"""

import logging
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import defaultdict

logger = logging.getLogger('data_agent')

# Cache for valid user IDs from baseline database
_valid_user_ids = None

# Known exfiltration domains (simplified list - expand as needed)
EXFIL_DOMAINS = {
    'dropbox.com', 'mega.nz', 'wetransfer.com', 'sendspace.com',
    'mediafire.com', 'rapidshare.com', 'fileserve.com'
}

# Known job search domains
JOBSEARCH_DOMAINS = {
    'linkedin.com', 'indeed.com', 'glassdoor.com', 'monster.com',
    'careerbuilder.com', 'ziprecruiter.com'
}


class SessionAggregator:
    """Aggregates StandardEvent objects into SessionInput format for Behavior Agent."""

    def __init__(self):
        """Initialize the aggregator."""
        self._load_valid_user_ids()

    def _load_valid_user_ids(self):
        """Load valid user IDs from baseline database (cached)."""
        global _valid_user_ids
        
        if _valid_user_ids is not None:
            return
        
        try:
            import sqlite3
            from pathlib import Path
            
            # Path to baselines database
            db_path = Path(__file__).parent.parent.parent.parent / 'data' / 'baselines.sqlite'
            
            if not db_path.exists():
                logger.warning(f"Baselines database not found: {db_path}")
                _valid_user_ids = []
                return
            
            # Load all user IDs
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM baselines')
            _valid_user_ids = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            logger.info(f"Loaded {len(_valid_user_ids)} valid user IDs from baseline database")
            
        except Exception as e:
            logger.error(f"Failed to load valid user IDs: {e}")
            _valid_user_ids = []

    def _get_random_valid_user_id(self) -> str:
        """Get a random user ID that has a baseline in the database."""
        if not _valid_user_ids:
            logger.warning("No valid user IDs available, using fallback")
            return "AAA0001"  # Fallback
        
        return random.choice(_valid_user_ids)

    def aggregate_events_to_sessions(
        self,
        events: List[Dict[str, Any]],
        time_window_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Aggregate events into user sessions.

        Args:
            events: List of StandardEvent dictionaries
            time_window_minutes: Time window for grouping events into sessions

        Returns:
            List of SessionInput dictionaries ready for Behavior Agent
        """
        if not events:
            logger.warning("No events to aggregate")
            return []

        # Group events by user_id
        events_by_user = defaultdict(list)
        for event in events:
            user_id = event.get('user_id', 'unknown')
            events_by_user[user_id].append(event)

        sessions = []
        for user_id, user_events in events_by_user.items():
            # Sort events by timestamp
            user_events.sort(key=lambda e: e.get('timestamp', ''))

            if not user_events:
                continue

            # Create a single session per user from all their events
            session = self._build_session_from_events(user_id, user_events)
            sessions.append(session)

        logger.info(f"Aggregated {len(events)} events into {len(sessions)} sessions")
        return sessions

    def _build_session_from_events(
        self,
        user_id: str,
        events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build a SessionInput from a list of events for a single user.

        Args:
            user_id: User identifier (will be replaced with valid baseline user)
            events: List of events for this user

        Returns:
            SessionInput dictionary
        """
        # Get first and last timestamps
        first_event = events[0]
        last_event = events[-1]

        first_ts = self._parse_timestamp(first_event.get('timestamp', ''))
        last_ts = self._parse_timestamp(last_event.get('timestamp', ''))

        # Calculate session duration
        duration_minutes = (last_ts - first_ts).total_seconds() / 60.0
        if duration_minutes < 1.0:
            duration_minutes = 1.0  # Minimum 1 minute

        # Extract device_id (pc)
        pc = first_event.get('device_id', 'unknown')

        # Calculate hour_of_day, is_weekend, is_outside_hours
        hour_of_day = first_ts.hour
        is_weekend = 1 if first_ts.weekday() >= 5 else 0
        is_outside_hours = 1 if hour_of_day < 8 or hour_of_day >= 18 else 0

        # Aggregate metrics from events
        file_count = 0
        max_sensitivity = 0
        usb_connected = 0
        usb_first_time = 0  # We don't have historical data, so always 0
        email_count = 0
        has_ext_email = 0
        visited_exfil_domain = 0
        visited_jobsearch_domain = 0

        for event in events:
            event_type = event.get('event_type', '')
            event_category = event.get('event_category', '')
            metadata = event.get('metadata', {})

            # Count file accesses
            if event_category == 'file' or event_type == 'file_access':
                file_count += 1
                # Track max sensitivity
                sensitivity = metadata.get('sensitivity_level', 0)
                if sensitivity > max_sensitivity:
                    max_sensitivity = sensitivity

            # Detect USB connections
            if event_type == 'device_connect' and metadata.get('is_usb'):
                usb_connected = 1

            # Count emails
            if event_category == 'email' or event_type in ['email_sent', 'email_received']:
                email_count += 1
                # Check for external emails
                if metadata.get('is_external'):
                    has_ext_email = 1

            # Check for exfil/jobsearch domains
            if event_category == 'web' or event_type == 'http_request':
                domain = metadata.get('domain', '')
                if domain:
                    if any(exfil in domain.lower() for exfil in EXFIL_DOMAINS):
                        visited_exfil_domain = 1
                    if any(job in domain.lower() for job in JOBSEARCH_DOMAINS):
                        visited_jobsearch_domain = 1

        # ── Network events extraction (for network agent) ───────────────────────────
        network_events = [
            e for e in events
            if e.get("event_type") == "network_connection"
        ]

        # CRITICAL: Replace real user_id with random valid user that has baseline
        valid_user_id = self._get_random_valid_user_id()
        
        logger.info(
            f"Mapped real user '{user_id}' → baseline user '{valid_user_id}' "
            f"({file_count} files, {email_count} emails, USB={usb_connected})"
        )

        # Build SessionInput with valid user_id
        session = {
            'user_id': valid_user_id,  # ← REPLACED with valid baseline user
            'pc': pc,
            'session_start': first_ts.isoformat(),
            'hour_of_day': hour_of_day,
            'is_weekend': is_weekend,
            'is_outside_hours': is_outside_hours,
            'duration_minutes': round(duration_minutes, 2),
            'file_count': file_count,
            'max_sensitivity': max_sensitivity,
            'usb_connected': usb_connected,
            'usb_first_time': usb_first_time,
            'email_count': email_count,
            'has_ext_email': has_ext_email,
            'visited_exfil_domain': visited_exfil_domain,
            'visited_jobsearch_domain': visited_jobsearch_domain,
            'simulated': False,  # Real data, not simulated
            # ADD THIS — raw network events for your agent
            'network_events': network_events,
        }

        return session

    def _parse_timestamp(self, ts_str: str) -> datetime:
        """Parse ISO 8601 timestamp string."""
        try:
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except Exception:
            # Fallback to current time if parsing fails
            return datetime.now()
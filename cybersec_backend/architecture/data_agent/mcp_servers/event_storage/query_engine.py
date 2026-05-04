"""
Query Engine for Event-Storage MCP Server

Provides filtering, pagination, summary statistics, and export capabilities
for stored StandardEvent objects.
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Generator
from collections import defaultdict

from mcp_servers.common.utils import create_error_response, parse_iso8601_timestamp

logger = logging.getLogger("event_storage")

# Platform-specific file locking
if sys.platform == 'win32':
    import msvcrt
    
    def lock_file(file_handle):
        """Lock file for Windows."""
        try:
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, 1)
        except IOError:
            pass  # File already locked, continue anyway
    
    def unlock_file(file_handle):
        """Unlock file for Windows."""
        try:
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
        except IOError:
            pass
else:
    import fcntl
    
    def lock_file(file_handle):
        """Lock file for Unix-like systems."""
        try:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
        except IOError:
            pass  # File already locked, continue anyway
    
    def unlock_file(file_handle):
        """Unlock file for Unix-like systems."""
        try:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
        except IOError:
            pass


def _read_event_files() -> Generator[Dict[str, Any], None, None]:
    """
    Generator that yields events from all event files in logs/ directory.
    Uses memory-efficient streaming to handle large datasets.
    
    Yields:
        Event dictionaries
    """
    logs_dir = Path("logs")
    
    if not logs_dir.exists():
        logger.warning("Logs directory does not exist")
        return
    
    # Find all event files
    event_files = sorted(logs_dir.glob("events_*.jsonl"))
    
    for file_path in event_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Acquire shared lock for concurrent read safety
                lock_file(f)
                
                try:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        
                        try:
                            event = json.loads(line)
                            yield event
                        except json.JSONDecodeError as e:
                            logger.warning(f"Corrupted event in {file_path} line {line_num}: {e}")
                            continue
                finally:
                    # Release lock
                    unlock_file(f)
        
        except Exception as e:
            logger.warning(f"Failed to read event file {file_path}: {e}")
            continue


def _apply_filters(
    event: Dict[str, Any],
    event_type: Optional[str] = None,
    event_category: Optional[str] = None,
    user_id: Optional[str] = None,
    device_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> bool:
    """
    Check if an event matches all specified filters.
    
    Args:
        event: Event dictionary
        event_type: Filter by event type
        event_category: Filter by event category
        user_id: Filter by user ID
        device_id: Filter by device ID
        start_time: Filter by start time (ISO 8601, inclusive)
        end_time: Filter by end time (ISO 8601, inclusive)
    
    Returns:
        True if event matches all filters, False otherwise
    """
    # Event type filter
    if event_type and event.get("event_type") != event_type:
        return False
    
    # Event category filter
    if event_category and event.get("event_category") != event_category:
        return False
    
    # User ID filter
    if user_id and event.get("user_id") != user_id:
        return False
    
    # Device ID filter
    if device_id and event.get("device_id") != device_id:
        return False
    
    # Time range filters (inclusive)
    if start_time or end_time:
        event_timestamp_str = event.get("timestamp")
        if not event_timestamp_str:
            return False
        
        event_time = parse_iso8601_timestamp(event_timestamp_str)
        if not event_time:
            logger.warning(f"Failed to parse event timestamp: {event_timestamp_str}")
            return False
        
        if start_time:
            start_dt = parse_iso8601_timestamp(start_time)
            if start_dt and event_time < start_dt:
                return False
        
        if end_time:
            end_dt = parse_iso8601_timestamp(end_time)
            if end_dt and event_time > end_dt:
                return False
    
    return True


def query_events(
    event_type: Optional[str] = None,
    event_category: Optional[str] = None,
    user_id: Optional[str] = None,
    device_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    page_size: int = 100,
    page: int = 1
) -> Dict[str, Any]:
    """
    Query stored events with filters and pagination.
    
    Args:
        event_type: Filter by event type
        event_category: Filter by event category
        user_id: Filter by user ID
        device_id: Filter by device ID
        start_time: Filter by start time (ISO 8601 format)
        end_time: Filter by end time (ISO 8601 format)
        page_size: Number of events per page (1-1000)
        page: Page number (1-indexed)
    
    Returns:
        Dictionary with events, count, pagination info
    """
    # Validate pagination parameters
    page_size = max(1, min(page_size, 1000))
    page = max(1, page)
    
    # Calculate offset
    offset = (page - 1) * page_size
    
    # Collect matching events
    matching_events = []
    total_matches = 0
    
    for event in _read_event_files():
        if _apply_filters(event, event_type, event_category, user_id, device_id, start_time, end_time):
            total_matches += 1
            
            # Skip events before current page
            if total_matches <= offset:
                continue
            
            # Collect events for current page
            if len(matching_events) < page_size:
                matching_events.append(event)
            else:
                # We have enough events for this page
                break
    
    # Check if there are more pages
    has_more = total_matches > (offset + len(matching_events))
    
    # Return empty result if no matches
    if total_matches == 0:
        logger.info("Query returned no matching events")
        return {
            "events": [],
            "count": 0,
            "total_matches": 0,
            "page": page,
            "page_size": page_size,
            "has_more": False,
            "message": "No events found matching the specified filters"
        }
    
    logger.info(f"Query returned {len(matching_events)} events (page {page}, total matches: {total_matches})")
    
    return {
        "events": matching_events,
        "count": len(matching_events),
        "total_matches": total_matches,
        "page": page,
        "page_size": page_size,
        "has_more": has_more
    }


def get_summary() -> Dict[str, Any]:
    """
    Get summary statistics about stored events.
    
    Returns:
        Dictionary with statistics (total count, counts by type/category,
        unique users/devices, time range)
    """
    total_count = 0
    events_by_type = defaultdict(int)
    events_by_category = defaultdict(int)
    unique_users = set()
    unique_devices = set()
    earliest_timestamp = None
    latest_timestamp = None
    
    for event in _read_event_files():
        total_count += 1
        
        # Count by type
        event_type = event.get("event_type")
        if event_type:
            events_by_type[event_type] += 1
        
        # Count by category
        event_category = event.get("event_category")
        if event_category:
            events_by_category[event_category] += 1
        
        # Track unique users and devices
        user_id = event.get("user_id")
        if user_id:
            unique_users.add(user_id)
        
        device_id = event.get("device_id")
        if device_id:
            unique_devices.add(device_id)
        
        # Track time range
        timestamp_str = event.get("timestamp")
        if timestamp_str:
            timestamp = parse_iso8601_timestamp(timestamp_str)
            if timestamp:
                if earliest_timestamp is None or timestamp < earliest_timestamp:
                    earliest_timestamp = timestamp
                if latest_timestamp is None or timestamp > latest_timestamp:
                    latest_timestamp = timestamp
    
    # Build summary response
    summary = {
        "total_events": total_count,
        "events_by_type": dict(events_by_type),
        "events_by_category": dict(events_by_category),
        "unique_users": len(unique_users),
        "unique_devices": len(unique_devices)
    }
    
    if earliest_timestamp and latest_timestamp:
        summary["time_range"] = {
            "earliest": earliest_timestamp.isoformat(),
            "latest": latest_timestamp.isoformat()
        }
    
    logger.info(f"Summary: {total_count} total events, {len(unique_users)} users, {len(unique_devices)} devices")
    
    return summary


def export_to_mailbox(
    event_type: Optional[str] = None,
    event_category: Optional[str] = None,
    user_id: Optional[str] = None,
    device_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> Dict[str, Any]:
    """
    Export filtered events to mailbox/clean_events.json for Team 2.
    
    Args:
        event_type: Filter by event type
        event_category: Filter by event category
        user_id: Filter by user ID
        device_id: Filter by device ID
        start_time: Filter by start time (ISO 8601 format)
        end_time: Filter by end time (ISO 8601 format)
    
    Returns:
        Success response with export details
    """
    # Create mailbox directory if it doesn't exist
    mailbox_dir = Path("mailbox")
    mailbox_dir.mkdir(parents=True, exist_ok=True)
    
    # Collect matching events
    matching_events = []
    
    for event in _read_event_files():
        if _apply_filters(event, event_type, event_category, user_id, device_id, start_time, end_time):
            matching_events.append(event)
    
    # Sort events by timestamp in ascending order
    matching_events.sort(key=lambda e: e.get("timestamp", ""))
    
    # Determine time range
    time_range = {}
    if matching_events:
        time_range = {
            "start": matching_events[0].get("timestamp"),
            "end": matching_events[-1].get("timestamp")
        }
    
    # Create metadata
    metadata = {
        "export_timestamp": datetime.now().isoformat(),
        "event_count": len(matching_events),
        "time_range": time_range,
        "data_source": "event_storage_mcp",
        "schema_version": "1.0",
        "filters_applied": {
            "event_type": event_type,
            "event_category": event_category,
            "user_id": user_id,
            "device_id": device_id,
            "start_time": start_time,
            "end_time": end_time
        }
    }
    
    # Write events to mailbox/clean_events.json
    events_file = mailbox_dir / "clean_events.json"
    metadata_file = mailbox_dir / "clean_events_metadata.json"
    
    try:
        # Write events with human-readable formatting
        with open(events_file, 'w', encoding='utf-8') as f:
            json.dump(matching_events, f, indent=2, default=str)
        
        # Write metadata
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        logger.info(f"Exported {len(matching_events)} events to {events_file}")
        
        return {
            "success": True,
            "events_exported": len(matching_events),
            "export_file": str(events_file),
            "metadata_file": str(metadata_file),
            "export_timestamp": metadata["export_timestamp"]
        }
    
    except Exception as e:
        logger.error(f"Failed to export events to mailbox: {e}")
        return create_error_response(
            "internal_error",
            f"Failed to export events: {str(e)}",
            {"mailbox_dir": str(mailbox_dir)}
        )

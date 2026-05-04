"""
Storage Engine for Event-Storage MCP Server

Handles persistent storage of StandardEvent objects in:
1. JSON Lines format (backup) - logs/events_YYYY-MM-DD.jsonl
2. Supabase PostgreSQL (primary) - cloud database

Hybrid approach ensures data safety with local backup and cloud scalability.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

from collectors.event_schema import StandardEvent
from mcp_servers.common.utils import create_error_response, create_success_response
from mcp_servers.event_storage.supabase_storage import SupabaseStorage

logger = logging.getLogger("event_storage")

# Initialize Supabase storage
supabase = SupabaseStorage()


def store_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Store an array of StandardEvent dictionaries to both JSON files and Supabase.
    
    Hybrid Storage Strategy:
    1. JSON Lines (backup) - Always stored locally for reliability
    2. Supabase (primary) - Cloud storage for Team 2 access
    
    Args:
        events: List of StandardEvent dictionaries
    
    Returns:
        Success response with count of stored events and storage locations
    """
    if not events:
        return create_error_response(
            "validation_error",
            "No events provided",
            {"events_count": 0}
        )
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Validate and organize events by date
    events_by_date = {}
    validated_events = []
    validated_count = 0
    validation_errors = []
    
    for idx, event_dict in enumerate(events):
        try:
            # Validate against StandardEvent schema
            validated_event = StandardEvent.model_validate(event_dict)
            
            # Parse timestamp to determine file
            timestamp_str = validated_event.timestamp
            try:
                # Handle ISO 8601 timestamps
                if 'T' in timestamp_str:
                    date_str = timestamp_str.split('T')[0]
                else:
                    # Fallback to current date if timestamp format is unexpected
                    date_str = datetime.now().strftime('%Y-%m-%d')
                
                # Group events by date
                if date_str not in events_by_date:
                    events_by_date[date_str] = []
                
                # Convert to dict for JSON serialization
                event_dict_validated = validated_event.model_dump(mode='json')
                events_by_date[date_str].append(event_dict_validated)
                validated_events.append(event_dict_validated)
                validated_count += 1
            
            except Exception as e:
                logger.warning(f"Failed to parse timestamp for event {idx}: {e}")
                validation_errors.append({
                    "index": idx,
                    "error": f"Invalid timestamp format: {str(e)}"
                })
        
        except Exception as e:
            logger.warning(f"Event validation failed for event {idx}: {e}")
            validation_errors.append({
                "index": idx,
                "error": str(e)
            })
    
    # STEP 1: Write events to JSON files (backup - always works)
    files_written = []
    for date_str, date_events in events_by_date.items():
        file_path = logs_dir / f"events_{date_str}.jsonl"
        
        try:
            # Append to existing file or create new one
            with open(file_path, 'a', encoding='utf-8') as f:
                for event in date_events:
                    # JSON Lines format: one event per line, no indentation
                    json_line = json.dumps(event, default=str)
                    f.write(json_line + '\n')
            
            files_written.append(str(file_path))
            logger.info(f"Stored {len(date_events)} events to {file_path}")
        
        except Exception as e:
            logger.error(f"Failed to write events to {file_path}: {e}")
            return create_error_response(
                "internal_error",
                f"Failed to write events: {str(e)}",
                {"file": str(file_path)}
            )
    
    # STEP 2: Store in Supabase (if enabled)
    supabase_result = supabase.store_events(validated_events)
    
    # Build response
    response = {
        "stored_count": validated_count,
        "files_written": files_written,
        "total_events": len(events),
        "supabase_enabled": supabase.enabled,
        "supabase_stored": supabase_result.get("stored", 0)
    }
    
    if validation_errors:
        response["validation_errors"] = validation_errors
        response["validation_error_count"] = len(validation_errors)
    
    if supabase_result.get("error"):
        response["supabase_error"] = supabase_result["error"]
        logger.warning(f"Supabase storage failed: {supabase_result['error']}")
    
    logger.info(
        f"Successfully stored {validated_count}/{len(events)} events "
        f"(JSON: {validated_count}, Supabase: {supabase_result.get('stored', 0)})"
    )
    
    return response

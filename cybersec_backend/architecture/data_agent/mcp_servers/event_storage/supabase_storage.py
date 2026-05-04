"""
Supabase Storage Module for Event-Storage MCP Server

Handles cloud storage of StandardEvent objects in Supabase PostgreSQL database.
Provides fallback mechanism if Supabase is unavailable.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("event_storage")

# Lazy import to avoid errors if supabase not installed
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase client not installed. Run: pip install supabase")


class SupabaseStorage:
    """
    Handles event storage in Supabase PostgreSQL database.
    
    Features:
    - Automatic connection management
    - Batch insert with upsert (handles duplicates)
    - Graceful fallback if Supabase unavailable
    - Detailed error logging
    """
    
    def __init__(self):
        """Initialize Supabase client if enabled"""
        self.client: Optional[Client] = None
        self.enabled = os.getenv("SUPABASE_ENABLED", "false").lower() == "true"
        
        if not SUPABASE_AVAILABLE:
            self.enabled = False
            logger.warning("Supabase storage disabled: client library not available")
            return
        
        if self.enabled:
            try:
                url = os.getenv("SUPABASE_URL")
                key = os.getenv("SUPABASE_KEY")
                
                if not url or not key:
                    logger.error("SUPABASE_URL or SUPABASE_KEY not set in .env")
                    self.enabled = False
                    return
                
                self.client = create_client(url, key)
                logger.info("Supabase storage initialized successfully")
            
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.enabled = False
    
    def store_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Store events in Supabase database.
        
        Args:
            events: List of StandardEvent dictionaries
        
        Returns:
            Dict with storage results:
            - stored: Number of events successfully stored
            - message: Success/error message
            - error: Error details (if failed)
        """
        if not self.enabled:
            return {
                "stored": 0,
                "message": "Supabase disabled",
                "skipped": True
            }
        
        if not events:
            return {
                "stored": 0,
                "message": "No events to store"
            }
        
        try:
            # Convert events to Supabase format
            db_events = [self._convert_event(e) for e in events]
            
            # Insert into Supabase with upsert (handles duplicates)
            result = self.client.table('events').upsert(
                db_events,
                on_conflict='event_id'
            ).execute()
            
            stored_count = len(result.data) if result.data else 0
            
            logger.info(f"Stored {stored_count} events to Supabase")
            
            return {
                "stored": stored_count,
                "message": "Success"
            }
        
        except Exception as e:
            logger.error(f"Supabase storage failed: {e}")
            return {
                "stored": 0,
                "error": str(e),
                "message": "Failed to store in Supabase"
            }
    
    def _convert_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert StandardEvent to Supabase table format.
        
        Args:
            event: StandardEvent dictionary
        
        Returns:
            Dictionary matching Supabase events table schema
        """
        return {
            "event_id": event["event_id"],
            "timestamp": event["timestamp"],
            "user_id": event["user_id"],
            "device_id": event["device_id"],
            "event_type": event["event_type"],
            "event_category": event["event_category"],
            "action": event["action"],
            "resource": event.get("resource", ""),
            "source": event["source"],
            "metadata": event.get("metadata", {})
        }
    
    def query_events(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Query events from Supabase database.
        
        Args:
            filters: Optional filters (event_type, event_category, user_id, etc.)
            limit: Maximum number of events to return
        
        Returns:
            List of event dictionaries
        """
        if not self.enabled:
            return []
        
        try:
            query = self.client.table('events').select('*')
            
            # Apply filters
            if filters:
                if filters.get('event_type'):
                    query = query.eq('event_type', filters['event_type'])
                if filters.get('event_category'):
                    query = query.eq('event_category', filters['event_category'])
                if filters.get('user_id'):
                    query = query.eq('user_id', filters['user_id'])
                if filters.get('device_id'):
                    query = query.eq('device_id', filters['device_id'])
            
            # Apply limit and order
            query = query.order('timestamp', desc=True).limit(limit)
            
            # Execute query
            result = query.execute()
            
            return result.data if result.data else []
        
        except Exception as e:
            logger.error(f"Supabase query failed: {e}")
            return []
    
    def get_event_count(self) -> int:
        """
        Get total number of events in Supabase.
        
        Returns:
            Total event count
        """
        if not self.enabled:
            return 0
        
        try:
            result = self.client.table('events').select('id', count='exact').execute()
            return result.count if hasattr(result, 'count') else 0
        
        except Exception as e:
            logger.error(f"Failed to get event count: {e}")
            return 0
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test Supabase connection.
        
        Returns:
            Dict with connection status
        """
        if not self.enabled:
            return {
                "connected": False,
                "message": "Supabase disabled"
            }
        
        try:
            # Try a simple query
            result = self.client.table('events').select('id').limit(1).execute()
            
            return {
                "connected": True,
                "message": "Connection successful"
            }
        
        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "message": "Connection failed"
            }

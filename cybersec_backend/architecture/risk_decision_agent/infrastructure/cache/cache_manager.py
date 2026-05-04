"""
SQLite-based Cache Manager for Decision Agent

Provides persistent caching with TTL support.
"""

import json
import sqlite3
import threading
from pathlib import Path
from time import time
from typing import Any, Dict, Optional


class CacheManager:
    """
    SQLite-based cache with TTL support.
    
    Features:
    - Persistent across restarts
    - Automatic expiration (TTL)
    - Thread-safe
    - Simple key-value interface
    """
    
    def __init__(self, db_path: str = "cache.db", default_ttl: int = 3600):
        """
        Initialize cache manager.
        
        Args:
            db_path: Path to SQLite database file
            default_ttl: Default time-to-live in seconds (default: 1 hour)
        """
        self.db_path = Path(db_path)
        self.default_ttl = default_ttl
        self._local = threading.local()
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=10.0
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            )
        """)
        
        # Create index for expiration queries
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at 
            ON cache(expires_at)
        """)
        
        conn.commit()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found/expired
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT value, expires_at FROM cache WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        # Check if expired
        if row['expires_at'] < time():
            # Delete expired entry
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()
            return None
        
        try:
            return json.loads(row['value'])
        except json.JSONDecodeError:
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (default: use default_ttl)
        """
        if ttl is None:
            ttl = self.default_ttl
        
        conn = self._get_connection()
        now = time()
        expires_at = now + ttl
        
        try:
            value_json = json.dumps(value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Value must be JSON-serializable: {e}")
        
        conn.execute(
            """
            INSERT OR REPLACE INTO cache (key, value, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (key, value_json, now, expires_at)
        )
        conn.commit()
    
    def delete(self, key: str):
        """Delete entry from cache."""
        conn = self._get_connection()
        conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        conn.commit()
    
    def clear(self):
        """Clear all cache entries."""
        conn = self._get_connection()
        conn.execute("DELETE FROM cache")
        conn.commit()
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "DELETE FROM cache WHERE expires_at < ?",
            (time(),)
        )
        conn.commit()
        return cursor.rowcount
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        conn = self._get_connection()
        
        # Total entries
        cursor = conn.execute("SELECT COUNT(*) as count FROM cache")
        total = cursor.fetchone()['count']
        
        # Expired entries
        cursor = conn.execute(
            "SELECT COUNT(*) as count FROM cache WHERE expires_at < ?",
            (time(),)
        )
        expired = cursor.fetchone()['count']
        
        # Database size
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
        
        return {
            "total_entries": total,
            "active_entries": total - expired,
            "expired_entries": expired,
            "db_size_bytes": db_size,
            "db_size_mb": round(db_size / (1024 * 1024), 2)
        }
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn'):
            self._local.conn.close()
            delattr(self._local, 'conn')


# Convenience functions for common cache patterns
def make_cache_key(*parts: str) -> str:
    """Create a cache key from multiple parts."""
    return ":".join(str(p) for p in parts)


if __name__ == "__main__":
    # Demo usage
    cache = CacheManager("test_cache.db", default_ttl=60)
    
    # Set some values
    cache.set("user:123", {"name": "Alice", "role": "admin"})
    cache.set("asset:456", {"type": "database", "sensitivity": "high"})
    
    # Get values
    user = cache.get("user:123")
    print(f"User: {user}")
    
    asset = cache.get("asset:456")
    print(f"Asset: {asset}")
    
    # Stats
    stats = cache.get_stats()
    print(f"\nCache stats: {stats}")
    
    # Cleanup
    removed = cache.cleanup_expired()
    print(f"Removed {removed} expired entries")
    
    cache.close()

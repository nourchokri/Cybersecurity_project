"""
In-memory baseline cache.
Loaded once at startup via BehaviorAgentConfig.ready().
All agent nodes read from this cache instead of opening SQLite per session.
"""
import json
import logging

logger = logging.getLogger('behavior_agent')

_baseline_cache: dict = {}   # {user_id: UserBaseline}
_cache_ready: bool = False


def warm_cache():
    """Load all baselines from SQLite into memory. Called once at startup."""
    global _baseline_cache, _cache_ready
    try:
        from django.conf import settings
        from ..scoring.baseline import get_connection, UserBaseline

        conn = get_connection()
        rows = conn.execute('SELECT user_id, data FROM baselines').fetchall()
        conn.close()

        _baseline_cache = {
            row[0]: UserBaseline(**json.loads(row[1]))
            for row in rows
        }
        _cache_ready = True
        logger.info(f'Baseline cache warmed: {len(_baseline_cache)} users')
    except Exception as e:
        logger.warning(f'Could not warm baseline cache: {e}')
        _cache_ready = False


def get_cached_baseline(user_id: str):
    """Return baseline from cache. Falls back to SQLite if cache not ready."""
    if _cache_ready and user_id in _baseline_cache:
        return _baseline_cache[user_id]

    # Fallback: direct SQLite read
    from ..scoring.baseline import get_connection, load_baseline
    conn = get_connection()
    b = load_baseline(conn, user_id)
    conn.close()
    return b


def update_cached_baseline(user_id: str, baseline):
    """Update the in-memory cache after scoring."""
    if _cache_ready:
        _baseline_cache[user_id] = baseline


def flush_cache_to_db():
    """Persist all in-memory baselines back to SQLite."""
    if not _cache_ready:
        return
    from ..scoring.baseline import get_connection, save_baseline
    conn = get_connection()
    for b in _baseline_cache.values():
        save_baseline(conn, b)
    conn.close()
    logger.info(f'Flushed {len(_baseline_cache)} baselines to SQLite')


def cache_size() -> int:
    return len(_baseline_cache)
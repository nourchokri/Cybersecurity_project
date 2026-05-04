"""
Persistent LangGraph checkpointer.

LangGraph 1.1.8 with langgraph-checkpoint-sqlite 3.x:
- AsyncSqliteSaver requires async context manager — not compatible with sync graph.invoke()
- InMemorySaver is the correct sync-compatible persistent saver in this version

We use InMemorySaver (LangGraph built-in) for the graph checkpointer,
and separately flush scored results to our own SQLite (agent_memory.db)
for long-term persistence across restarts.
"""
import json
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger('behavior_agent')

_checkpointer = None
_memory_conn  = None


def get_checkpointer():
    """
    Return InMemorySaver for LangGraph graph compilation.
    Compatible with sync graph.invoke() in LangGraph 1.1.8.
    """
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    from langgraph.checkpoint.memory import MemorySaver
    _checkpointer = MemorySaver()
    logger.info('MemorySaver checkpointer initialised (sync-compatible)')
    return _checkpointer


def _get_memory_conn():
    """SQLite connection for our own persistent session history."""
    global _memory_conn
    if _memory_conn is not None:
        return _memory_conn

    from django.conf import settings
    db_path = str(getattr(settings, 'AGENT_MEMORY_DB',
                          Path(settings.BASE_DIR) / 'data' / 'agent_memory.db'))

    _memory_conn = sqlite3.connect(db_path, check_same_thread=False)
    _memory_conn.execute("""
        CREATE TABLE IF NOT EXISTS session_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id   TEXT NOT NULL,
            user_id     TEXT NOT NULL,
            timestamp   TEXT,
            score       REAL,
            verdict     TEXT,
            flagged     INTEGER,
            result_json TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _memory_conn.commit()
    logger.info(f'Session history DB initialised at {db_path}')
    return _memory_conn


def save_session_result(thread_id: str, anomaly_result: dict):
    """Persist a scored session result to the history DB."""
    try:
        conn = _get_memory_conn()
        conn.execute(
            """INSERT INTO session_history
               (thread_id, user_id, timestamp, score, verdict, flagged, result_json)
               VALUES (?,?,?,?,?,?,?)""",
            (
                thread_id,
                anomaly_result.get('user_id', ''),
                anomaly_result.get('timestamp', ''),
                anomaly_result.get('combined_score', 0),
                anomaly_result.get('detection_agent_analysis', {}).get('verdict', ''),
                int(anomaly_result.get('flagged', False)),
                json.dumps(anomaly_result, default=str),
            )
        )
        conn.commit()
    except Exception as e:
        logger.warning(f'Failed to save session history: {e}')


def get_user_history(user_id: str, limit: int = 5) -> list:
    """Retrieve recent scored sessions for a user (for LLM context)."""
    try:
        conn = _get_memory_conn()
        rows = conn.execute(
            """SELECT score, verdict, flagged, timestamp
               FROM session_history
               WHERE user_id=?
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit)
        ).fetchall()
        return [{'score': r[0], 'verdict': r[1], 'flagged': bool(r[2]), 'timestamp': r[3]}
                for r in rows]
    except Exception:
        return []


def get_previous_result(thread_id: str) -> dict | None:
    """Retrieve the most recent anomaly_result for a thread_id."""
    try:
        conn = _get_memory_conn()
        row = conn.execute(
            """SELECT result_json FROM session_history
               WHERE thread_id=? ORDER BY created_at DESC LIMIT 1""",
            (thread_id,)
        ).fetchone()
        if row:
            return json.loads(row[0])
    except Exception:
        pass
    return None
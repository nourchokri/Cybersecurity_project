from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def _require_psycopg():
    try:
        import psycopg  # type: ignore
        from psycopg import sql  # type: ignore

        return psycopg, sql
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "psycopg is required for DB-backed CERT tools. Install with: pip install 'psycopg[binary]'"
        ) from e


def require_sql():
    """Return psycopg.sql module for safe SQL composition."""
    _, sql = _require_psycopg()
    return sql


def _ident(sql_module, name: str):
    """Build a psycopg.sql.Identifier for a possibly schema-qualified name."""
    parts = [p for p in (name or "").split(".") if p]
    if not parts:
        raise ValueError("empty identifier")
    return sql_module.Identifier(*parts)


@dataclass(frozen=True)
class TableSchema:
    table: str
    columns: Tuple[str, ...]

    def has(self, col: str) -> bool:
        return col in self.columns

    def pick(self, *candidates: str) -> Optional[str]:
        for c in candidates:
            if c in self.columns:
                return c
        return None


class CertDb:
    """Thin wrapper around Supabase Postgres for CERT tools.

    - Opens a new connection per operation (simple + safe).
    - Caches table schemas (column lists) to handle different CSV header variants.
    """

    def __init__(self, dsn: str):
        self._dsn = dsn

    def connect(self):
        psycopg, _ = _require_psycopg()
        return psycopg.connect(self._dsn, autocommit=True)

    def fetch_one(self, sql_text: Any, params: Sequence[Any] | None = None) -> Tuple[Any, ...]:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_text, params or ())
                row = cur.fetchone()
                if row is None:
                    raise ValueError("Query returned no rows")
                return tuple(row)

    def fetch_all(self, sql_text: Any, params: Sequence[Any] | None = None) -> List[Tuple[Any, ...]]:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_text, params or ())
                rows = cur.fetchall() or []
                return [tuple(r) for r in rows]

    @lru_cache(maxsize=128)
    def table_schema(self, table: str) -> TableSchema:
        """Return the (cached) list of columns for a given table."""
        psycopg, sql = _require_psycopg()

        # information_schema expects unquoted name components.
        parts = [p for p in table.split(".") if p]
        if len(parts) == 1:
            schema, name = "public", parts[0]
        else:
            schema, name = parts[-2], parts[-1]

        q = sql.SQL(
            """
            select column_name
            from information_schema.columns
            where table_schema = %s and table_name = %s
            order by ordinal_position
            """
        )
        rows = self.fetch_all(q, (schema, name))
        cols = tuple(str(r[0]) for r in rows)
        if not cols:
            raise ValueError(f"Could not find columns for table: {table}")
        return TableSchema(table=table, columns=cols)


def sql_ident(name: str):
    """Public helper for building Identifiers inside tool modules."""
    _, sql = _require_psycopg()
    return _ident(sql, name)

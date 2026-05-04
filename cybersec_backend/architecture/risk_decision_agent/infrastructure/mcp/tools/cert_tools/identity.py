from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from .config import CertDbConfig
from .db import CertDb, require_sql, sql_ident
from .parsing import format_iso, parse_timestamp


@dataclass
class IdentityTool:
    config: CertDbConfig

    def __post_init__(self) -> None:
        self.config = self.config.resolve()
        self._db = CertDb(self.config.dsn)

    def get_user_context(self, user_id: str, timestamp: str) -> Dict[str, Any]:
        """identity.get_user_context(user_id, timestamp)

        Returns a compact user profile combining:
        - LDAP monthly snapshot lookup (org metadata)
        - Psychometrics (O/C/E/A/N) if available
        """

        uid = (user_id or "").strip()
        if not uid:
            raise ValueError("user_id is required")

        ts = parse_timestamp(timestamp)

        # Pick the latest snapshot_month <= ts. If none exists for that user, fall back
        # to earliest snapshot for that user (mirrors the old "earliest available" fallback).
        sql = require_sql()
        ldap_t = sql_ident(self.config.ldap_table)

        q_latest = sql.SQL(
            """
            select snapshot_month, employee_name, email, role, business_unit, functional_unit,
                   department, team, supervisor
            from {ldap}
            where user_id = %s and snapshot_month <= %s::date
            order by snapshot_month desc
            limit 1
            """
        ).format(ldap=ldap_t)

        q_earliest = sql.SQL(
            """
            select snapshot_month, employee_name, email, role, business_unit, functional_unit,
                   department, team, supervisor
            from {ldap}
            where user_id = %s
            order by snapshot_month asc
            limit 1
            """
        ).format(ldap=ldap_t)

        org: Optional[Dict[str, Any]] = None
        ldap_snapshot = None
        try:
            row = self._db.fetch_one(q_latest, (uid, ts.date()))
        except ValueError:
            row = None
        if row is None:
            try:
                row = self._db.fetch_one(q_earliest, (uid,))
            except ValueError:
                row = None

        if row is not None:
            snapshot_month = row[0]
            ldap_snapshot = str(snapshot_month)[:7] if snapshot_month is not None else None
            org = {
                "employee_name": row[1],
                "email": row[2],
                "role": row[3],
                "business_unit": row[4],
                "functional_unit": row[5],
                "department": row[6],
                "team": row[7],
                "supervisor": row[8],
            }

        psych_t = sql_ident(self.config.psych_table)
        psych_schema = self._db.table_schema(self.config.psych_table)
        user_id_col = psych_schema.pick("user_id", "user")
        emp_col = psych_schema.pick("employee_name", "employee") or "employee_name"
        o_col = psych_schema.pick("O", "o")
        c_col = psych_schema.pick("C", "c")
        e_col = psych_schema.pick("E", "e")
        a_col = psych_schema.pick("A", "a")
        n_col = psych_schema.pick("N", "n")

        if not user_id_col:
            raise ValueError(f"psychometrics table is missing user id column: {self.config.psych_table}")

        cols = [sql.Identifier(emp_col)]
        for col in (o_col, c_col, e_col, a_col, n_col):
            if col is not None:
                cols.append(sql.Identifier(col))
            else:
                cols.append(sql.SQL("null"))

        q_psych = sql.SQL("select {emp}, {o}, {c}, {e}, {a}, {n} from {psych} where {uid} = %s limit 1").format(
            emp=cols[0],
            o=cols[1],
            c=cols[2],
            e=cols[3],
            a=cols[4],
            n=cols[5],
            psych=psych_t,
            uid=sql.Identifier(user_id_col),
        )

        psych: Optional[Dict[str, Any]] = None
        try:
            prow = self._db.fetch_one(q_psych, (uid,))
            psych = {
                "employee_name": prow[0],
                "O": _safe_int(prow[1]),
                "C": _safe_int(prow[2]),
                "E": _safe_int(prow[3]),
                "A": _safe_int(prow[4]),
                "N": _safe_int(prow[5]),
            }
        except ValueError:
            psych = None

        return {
            "user_id": uid,
            "timestamp": format_iso(ts),
            "ldap_snapshot": ldap_snapshot,
            "org": org,
            "psychometrics": psych,
            "sources": {
                "ldap": self.config.ldap_table,
                "psychometrics": self.config.psych_table,
            },
        }


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except Exception:
        return None

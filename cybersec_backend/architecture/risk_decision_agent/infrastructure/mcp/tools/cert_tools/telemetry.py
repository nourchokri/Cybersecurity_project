from __future__ import annotations

import math
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional, Tuple

from .config import CertDbConfig
from .db import CertDb, require_sql, sql_ident
from .parsing import TimeWindow, format_iso, parse_timestamp


def _split_recipients(value: Optional[str]) -> List[str]:
    if not value:
        return []
    # CERT uses ';' between emails; be forgiving.
    parts: List[str] = []
    for chunk in value.replace(",", ";").split(";"):
        c = chunk.strip()
        if c:
            parts.append(c)
    return parts


def _domain(email: str) -> Optional[str]:
    if "@" not in email:
        return None
    return email.split("@", 1)[1].lower().strip() or None


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


@dataclass
class TelemetryTool:
    config: CertDbConfig

    def __post_init__(self) -> None:
        self.config = self.config.resolve()
        self._db = CertDb(self.config.dsn)
        self._sql = require_sql()

    def get_user_summary(self, user_id: str, start_ts: str, end_ts: str) -> Dict[str, Any]:
        """telemetry.get_user_summary(user_id, start_ts, end_ts)

        Output is aggregated/compact (no raw rows).
        """

        uid = (user_id or "").strip()
        if not uid:
            raise ValueError("user_id is required")

        window = TimeWindow(parse_timestamp(start_ts), parse_timestamp(end_ts))

        summary: Dict[str, Any] = {
            "user_id": uid,
            "window": {"start_ts": format_iso(window.start), "end_ts": format_iso(window.end)},
            "tables": {},
        }

        # Decision Agent scope (per your pipeline split): only email + file.
        summary["tables"]["email"] = self._summarize_email(uid, window)
        summary["tables"]["file"] = self._summarize_file(uid, window)

        return summary

    def get_user_baseline(
        self,
        user_id: str,
        as_of_ts: str,
        lookback_days: int = 30,
    ) -> Dict[str, Any]:
        """telemetry.get_user_baseline(user_id, as_of_ts, lookback_days=30)

        Baseline describes what is "normal" for the user.
        """

        uid = (user_id or "").strip()
        if not uid:
            raise ValueError("user_id is required")

        as_of = parse_timestamp(as_of_ts)
        lookback_days = int(lookback_days)
        if lookback_days <= 0 or lookback_days > 3650:
            raise ValueError("lookback_days must be in 1..3650")

        start = as_of - timedelta(days=lookback_days)
        window = TimeWindow(start, as_of)

        summary = self.get_user_summary(uid, format_iso(window.start), format_iso(window.end))

        daily_counts = self._daily_counts(uid, window)

        baseline: Dict[str, Any] = {
            "user_id": uid,
            "as_of_ts": format_iso(as_of),
            "lookback_days": lookback_days,
            "window": {"start_ts": format_iso(window.start), "end_ts": format_iso(window.end)},
            "typical": {
                "pcs": {
                    "top": _top_items(summary["tables"].get("email", {}).get("top_pcs", []), 3)
                    or _top_items(summary["tables"].get("file", {}).get("top_pcs", []), 3)
                },
                "recipients": _top_items(summary["tables"].get("email", {}).get("top_recipients", []), 5),
            },
            "daily": daily_counts,
            "summary": summary,
        }

        return baseline

    def get_deviations(
        self,
        user_id: str,
        start_ts: str,
        end_ts: str,
        baseline: Dict[str, Any],
    ) -> Dict[str, Any]:
        """telemetry.get_deviations(user_id, start_ts, end_ts, baseline)

        Returns top deviations (z-scores/percentiles where possible) and a short list
        of "why it's weird" explanations.
        """

        uid = (user_id or "").strip()
        if not uid:
            raise ValueError("user_id is required")

        window = TimeWindow(parse_timestamp(start_ts), parse_timestamp(end_ts))
        current = self.get_user_summary(uid, format_iso(window.start), format_iso(window.end))

        deviations: List[Dict[str, Any]] = []
        why: List[str] = []

        # Compare event rates per day against baseline mean/std when available.
        baseline_daily = (baseline or {}).get("daily", {})

        for table in ("email", "file"):
            cur_count = int(current.get("tables", {}).get(table, {}).get("count", 0) or 0)
            cur_rate = cur_count / window.days

            stats = baseline_daily.get(table, {}).get("count", {})
            mu = stats.get("mean")
            sigma = stats.get("stdev")
            z = None
            if mu is not None and sigma is not None and sigma > 1e-9:
                z = (cur_rate - mu) / sigma

            deviations.append(
                {
                    "metric": f"{table}.count_per_day",
                    "current": round(cur_rate, 4),
                    "baseline_mean": mu,
                    "baseline_stdev": sigma,
                    "z_score": round(z, 3) if z is not None else None,
                }
            )

            if z is not None and abs(z) >= 3.0:
                why.append(f"{table} volume is unusual (z={z:+.2f})")

        # New/rare PCs vs baseline typical set (derived from email+file PCs).
        base_pcs = set((baseline or {}).get("typical", {}).get("pcs", {}).get("top", []) or [])
        cur_pcs = set((current.get("tables", {}).get("email", {}).get("unique_pcs") or [])) | set(
            (current.get("tables", {}).get("file", {}).get("unique_pcs") or [])
        )
        new_pcs = sorted(p for p in cur_pcs if p and p not in base_pcs)
        if new_pcs:
            deviations.append(
                {
                    "metric": "telemetry.new_pcs",
                    "current": new_pcs[:10],
                    "baseline_top_pcs": sorted(base_pcs),
                    "z_score": None,
                }
            )
            why.append("user used PCs not typical for them")

        # Recipients: new top recipients
        base_rcpts = set((baseline or {}).get("typical", {}).get("recipients") or [])
        cur_top_rcpts = [r["value"] for r in (current.get("tables", {}).get("email", {}).get("top_recipients") or [])]
        new_rcpts = [r for r in cur_top_rcpts if r and r not in base_rcpts]
        if new_rcpts:
            deviations.append(
                {
                    "metric": "email.new_top_recipients",
                    "current": new_rcpts[:10],
                    "baseline_top_recipients": sorted(base_rcpts),
                    "z_score": None,
                }
            )
            why.append("user emailed recipients not typical for them")

        # Sort deviations with z-score (absolute) first, then the rest.
        def sort_key(item: Dict[str, Any]) -> Tuple[int, float]:
            z = item.get("z_score")
            if z is None:
                return (1, 0.0)
            return (0, -abs(float(z)))

        deviations_sorted = sorted(deviations, key=sort_key)

        return {
            "user_id": uid,
            "window": {"start_ts": format_iso(window.start), "end_ts": format_iso(window.end)},
            "deviations": deviations_sorted[:10],
            "why_weird": why[:10],
            "current_summary": current,
        }

    # -----------------
    # Internals
    # -----------------

    def _summarize_email(self, user_id: str, window: TimeWindow) -> Dict[str, Any]:
        t = self.config.email_table
        schema = self._db.table_schema(t)

        user_col = schema.pick("user", "user_id")
        date_col = schema.pick("date", "timestamp", "time")
        pc_col = schema.pick("pc")
        size_col = schema.pick("size")
        att_col = schema.pick("attachments")
        to_col = schema.pick("to")
        cc_col = schema.pick("cc")
        bcc_col = schema.pick("bcc")

        if not user_col or not date_col:
            return {"available": False, "reason": f"missing required columns in {t}: need user/date"}

        sql = self._sql
        tbl = sql_ident(t)
        u = sql.Identifier(user_col)
        d = sql.Identifier(date_col)

        q_counts = sql.SQL(
            "select count(*)::bigint, coalesce(sum({size})::bigint,0), coalesce(sum({att})::bigint,0) "
            "from {tbl} where {u}=%s and {d}>= %s and {d}<= %s"
        ).format(
            size=sql.Identifier(size_col) if size_col else sql.SQL("0"),
            att=sql.Identifier(att_col) if att_col else sql.SQL("0"),
            tbl=tbl,
            u=u,
            d=d,
        )

        count, total_size, total_attachments = self._db.fetch_one(
            q_counts, (user_id, window.start, window.end)
        )

        # PCs
        unique_pcs: List[str] = []
        top_pcs: List[Dict[str, Any]] = []
        if pc_col:
            pc = sql.Identifier(pc_col)
            q_unique = sql.SQL(
                "select distinct {pc} from {tbl} where {u}=%s and {d}>= %s and {d}<= %s "
                "and {pc} is not null and trim(cast({pc} as text)) <> '' order by {pc} limit 50"
            ).format(pc=pc, tbl=tbl, u=u, d=d)
            unique_pcs = [str(r[0]) for r in self._db.fetch_all(q_unique, (user_id, window.start, window.end))]

            q_top = sql.SQL(
                "select {pc}, count(*)::bigint from {tbl} where {u}=%s and {d}>= %s and {d}<= %s "
                "and {pc} is not null and trim(cast({pc} as text)) <> '' group by {pc} order by 2 desc limit 5"
            ).format(pc=pc, tbl=tbl, u=u, d=d)
            top_pcs = [{"value": str(v), "count": int(c)} for (v, c) in self._db.fetch_all(q_top, (user_id, window.start, window.end))]

        # Recipients + domains
        top_recipients: List[Dict[str, Any]] = []
        top_domains: List[Dict[str, Any]] = []

        rcpt_cols = [c for c in [to_col, cc_col, bcc_col] if c]
        if rcpt_cols:
            # Build a UNION ALL over recipient columns.
            parts = []
            for c in rcpt_cols:
                col = sql.Identifier(c)
                parts.append(
                    sql.SQL(
                        "select lower(trim(x)) as r from {tbl}, regexp_split_to_table(coalesce({col}, ''), '[;,]') x "
                        "where {u}=%s and {d}>= %s and {d}<= %s"
                    ).format(tbl=tbl, col=col, u=u, d=d)
                )
            union = sql.SQL(" union all ").join(parts)

            q_rcpt = sql.SQL(
                "with rcpt as ({union}) "
                "select r, count(*)::bigint from rcpt where r is not null and r<>'' group by r order by 2 desc limit 5"
            ).format(union=union)
            top_recipients = [
                {"value": str(r), "count": int(c)}
                for (r, c) in self._db.fetch_all(q_rcpt, (user_id, window.start, window.end) * len(rcpt_cols))
            ]

            q_dom = sql.SQL(
                "with rcpt as ({union}) "
                "select split_part(r,'@',2) as d, count(*)::bigint "
                "from rcpt where position('@' in r) > 0 group by d order by 2 desc limit 5"
            ).format(union=union)
            top_domains = [
                {"value": str(dom), "count": int(c)}
                for (dom, c) in self._db.fetch_all(q_dom, (user_id, window.start, window.end) * len(rcpt_cols))
                if dom
            ]

        return {
            "available": True,
            "count": int(count or 0),
            "total_size": int(total_size or 0),
            "total_attachments": int(total_attachments or 0),
            "unique_pcs": unique_pcs[:50],
            "top_pcs": top_pcs,
            "top_recipients": top_recipients,
            "top_recipient_domains": top_domains,
        }

    def _summarize_file(self, user_id: str, window: TimeWindow) -> Dict[str, Any]:
        t = self.config.file_table
        schema = self._db.table_schema(t)

        user_col = schema.pick("user", "user_id")
        date_col = schema.pick("date", "timestamp", "time")
        pc_col = schema.pick("pc")
        file_col = schema.pick("fname", "filename")
        sensitivity_col = schema.pick("sensitivity_level", "sensitivity")

        if not user_col or not date_col or not file_col:
            return {
                "available": False,
                "reason": f"missing required columns in {t}: need user/date and fname/filename",
            }

        sql = self._sql
        tbl = sql_ident(t)
        u = sql.Identifier(user_col)
        d = sql.Identifier(date_col)
        fcol = sql.Identifier(file_col)

        q_count = sql.SQL(
            "select count(*)::bigint from {tbl} where {u}=%s and {d}>= %s and {d}<= %s"
        ).format(tbl=tbl, u=u, d=d)
        (count,) = self._db.fetch_one(q_count, (user_id, window.start, window.end))

        unique_pcs: List[str] = []
        top_pcs: List[Dict[str, Any]] = []
        if pc_col:
            pc = sql.Identifier(pc_col)
            q_unique = sql.SQL(
                "select distinct {pc} from {tbl} where {u}=%s and {d}>= %s and {d}<= %s "
                "and {pc} is not null and trim(cast({pc} as text)) <> '' order by {pc} limit 50"
            ).format(pc=pc, tbl=tbl, u=u, d=d)
            unique_pcs = [str(r[0]) for r in self._db.fetch_all(q_unique, (user_id, window.start, window.end))]

            q_top = sql.SQL(
                "select {pc}, count(*)::bigint from {tbl} where {u}=%s and {d}>= %s and {d}<= %s "
                "and {pc} is not null and trim(cast({pc} as text)) <> '' group by {pc} order by 2 desc limit 5"
            ).format(pc=pc, tbl=tbl, u=u, d=d)
            top_pcs = [{"value": str(v), "count": int(c)} for (v, c) in self._db.fetch_all(q_top, (user_id, window.start, window.end))]

        q_top_files = sql.SQL(
            "select {f}, count(*)::bigint from {tbl} where {u}=%s and {d}>= %s and {d}<= %s "
            "and {f} is not null and trim(cast({f} as text)) <> '' group by {f} order by 2 desc limit 5"
        ).format(f=fcol, tbl=tbl, u=u, d=d)
        top_filenames = [
            {"value": str(v), "count": int(c)}
            for (v, c) in self._db.fetch_all(q_top_files, (user_id, window.start, window.end))
        ]

        # Extension counts: take substring after last '.'; ignore names without a dot.
        q_ext = sql.SQL(
            """
                        select lower(regexp_replace(cast({f} as text), '^.*\\.', '')) as ext,
                   count(*)::bigint
            from {tbl}
            where {u}=%s and {d}>= %s and {d}<= %s
              and position('.' in cast({f} as text)) > 0
            group by ext
            order by 2 desc
            limit 5
            """
        ).format(f=fcol, tbl=tbl, u=u, d=d)

        top_ext = [
            {"value": str(ext), "count": int(c)}
            for (ext, c) in self._db.fetch_all(q_ext, (user_id, window.start, window.end))
            if ext
        ]

        # Sensitivity distribution (optional column).
        sensitivity_distribution: List[Dict[str, Any]] = []
        if sensitivity_col:
            scol = sql.Identifier(sensitivity_col)
            q_sens = sql.SQL(
                "select {s}, count(*)::bigint from {tbl} where {u}=%s and {d}>= %s and {d}<= %s "
                "and {s} is not null and trim(cast({s} as text)) <> '' group by {s} order by 2 desc limit 5"
            ).format(s=scol, tbl=tbl, u=u, d=d)
            sensitivity_distribution = [
                {"value": str(v), "count": int(c)}
                for (v, c) in self._db.fetch_all(q_sens, (user_id, window.start, window.end))
            ]

        return {
            "available": True,
            "count": int(count or 0),
            "unique_pcs": unique_pcs[:50],
            "top_pcs": top_pcs,
            "top_filenames": top_filenames,
            "top_extensions": top_ext,
            "sensitivity_distribution": sensitivity_distribution,
        }

    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """telemetry.get_file_metadata(file_id)

        Look up a single `cert_file` row by primary id.

        Intended for enriching an anomaly event where `entity_id` is the `cert_file.id`.
        Returns a compact dict with `filename`, `sensitivity_level` (if present), and a
        derived `data_type` (file extension).

        If `cert_file` includes `user` and `date` columns, these are returned as both:
        - `user_id` / `last_seen` (legacy naming)
        - `created_by` / `created_at` (aliases; helpful for downstream reasoning)

        Note: this lookup intentionally does NOT fetch any large/freeform content fields
        such as a `context` column (if present in your schema).
        """

        fid = (file_id or "").strip()
        if not fid:
            raise ValueError("file_id is required")

        schema = self._db.table_schema(self.config.file_table)
        id_col = schema.pick("id", "entity_id", "file_id")
        file_col = schema.pick("filename", "fname")
        sensitivity_col = schema.pick("sensitivity_level", "sensitivity")
        user_col = schema.pick("user", "user_id")
        pc_col = schema.pick("pc")
        date_col = schema.pick("date", "timestamp", "time")

        if not id_col or not file_col:
            return {
                "available": False,
                "reason": f"cert_file missing required columns (id={id_col}, filename={file_col})",
                "entity_id": fid,
            }

        sql = self._sql
        tbl = sql_ident(self.config.file_table)
        id_ident = sql.Identifier(id_col)
        f_ident = sql.Identifier(file_col)
        s_ident = sql.Identifier(sensitivity_col) if sensitivity_col else sql.SQL("null")
        u_ident = sql.Identifier(user_col) if user_col else sql.SQL("null")
        p_ident = sql.Identifier(pc_col) if pc_col else sql.SQL("null")
        d_ident = sql.Identifier(date_col) if date_col else sql.SQL("null")

        q = sql.SQL("select {f}, {s}, {u}, {p}, {d} from {tbl} where {id}=%s limit 1").format(
            f=f_ident,
            s=s_ident,
            u=u_ident,
            p=p_ident,
            d=d_ident,
            tbl=tbl,
            id=id_ident,
        )

        try:
            filename, sensitivity, user_id, pc, last_seen = self._db.fetch_one(q, (fid,))
        except ValueError:
            return {
                "available": False,
                "reason": "cert_file row not found",
                "entity_id": fid,
            }

        filename_s = str(filename) if filename is not None else ""
        ext = Path(filename_s).suffix.lower().lstrip(".")
        data_type = ext or "unknown"

        return {
            "available": True,
            "entity_id": fid,
            "filename": filename_s or None,
            "sensitivity_level": (str(sensitivity).strip() if sensitivity is not None else None),
            "data_type": data_type,
            "user_id": (str(user_id).strip() if user_id is not None else None),
            "pc": (str(pc).strip() if pc is not None else None),
            "last_seen": (str(last_seen) if last_seen is not None else None),
            "created_by": (str(user_id).strip() if user_id is not None else None),
            "created_at": (str(last_seen) if last_seen is not None else None),
            "sources": {"cert_file": self.config.file_table},
        }

    def _daily_counts(self, user_id: str, window: TimeWindow) -> Dict[str, Any]:
        out: Dict[str, Any] = {}

        def per_day_counts(table: str) -> List[int]:
            if table == "email":
                t = self.config.email_table
            else:
                t = self.config.file_table

            schema = self._db.table_schema(t)
            user_col = schema.pick("user", "user_id")
            date_col = schema.pick("date", "timestamp", "time")
            if not user_col or not date_col:
                return []

            sql = self._sql
            tbl = sql_ident(t)
            u = sql.Identifier(user_col)
            d = sql.Identifier(date_col)

            q = sql.SQL(
                "select date_trunc('day', {d})::date as day, count(*)::bigint "
                "from {tbl} where {u}=%s and {d}>= %s and {d}<= %s group by day order by day"
            ).format(d=d, tbl=tbl, u=u)

            rows = self._db.fetch_all(q, (user_id, window.start, window.end))
            return [int(r[1]) for r in rows]

        for table in ("email", "file"):
            series = per_day_counts(table)
            if not series:
                out[table] = {"count": {"mean": 0.0, "stdev": 0.0}, "days_observed": 0}
                continue

            mu = mean(series)
            sigma = pstdev(series) if len(series) > 1 else 0.0
            out[table] = {
                "count": {"mean": round(mu, 4), "stdev": round(sigma, 4)},
                "days_observed": len(series),
            }

        return out


def _top_items(items: Any, n: int) -> List[str]:
    # Accept either [{value,count}...] or raw list.
    if not items:
        return []
    if isinstance(items, list) and items and isinstance(items[0], dict) and "value" in items[0]:
        return [str(x.get("value")) for x in items[:n] if x.get("value") is not None]
    return [str(x) for x in list(items)[:n]]

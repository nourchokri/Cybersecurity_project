from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


_CERT_FORMATS = (
    "%m/%d/%Y %H:%M:%S",  # CERT default
    "%Y-%m-%dT%H:%M:%S.%f",  # ISO with micros
    "%Y-%m-%dT%H:%M:%S",  # ISO
)


def parse_timestamp(value: str) -> datetime:
    """Parse a timestamp string into a naive datetime (local/unspecified tz).

    We keep it naive because CERT CSVs are naive and we only do relative comparisons.
    """

    v = (value or "").strip()
    if not v:
        raise ValueError("empty timestamp")

    # Common case: ISO ending with Z
    if v.endswith("Z"):
        v = v[:-1]

    for fmt in _CERT_FORMATS:
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            pass

    # Last resort: try fromisoformat for variants
    try:
        return datetime.fromisoformat(v)
    except ValueError as e:
        raise ValueError(f"unsupported timestamp format: {value!r}") from e


def format_iso(dt: datetime) -> str:
    return dt.replace(tzinfo=None).isoformat()


@dataclass(frozen=True)
class TimeWindow:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("end < start")

    @property
    def days(self) -> float:
        seconds = (self.end - self.start).total_seconds()
        return max(1e-9, seconds / 86400.0)

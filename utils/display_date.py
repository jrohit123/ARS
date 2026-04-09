"""Human-readable dates: dd-MMM-yy (e.g. 10-Apr-26). English month names, consistent on all platforms."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

_MONTH = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def _coerce_to_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(s[:10], fmt).date()
            except ValueError:
                continue
        try:
            return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").date()
        except ValueError:
            pass
        try:
            norm = s.replace("Z", "+00:00")
            if " " in norm and "T" not in norm[:11]:
                norm = norm.replace(" ", "T", 1)
            if "." in norm:
                norm = norm.split(".")[0]
            return datetime.fromisoformat(norm).date()
        except ValueError:
            pass
    return None


def format_display_date(value: Any) -> str:
    """Format a date for display. Empty/unknown → em dash. Unparseable non-empty string returned as-is."""
    if value is None or value == "":
        return "—"
    d = _coerce_to_date(value)
    if d is not None:
        return f"{d.day:02d}-{_MONTH[d.month - 1]}-{d.year % 100:02d}"
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "—"

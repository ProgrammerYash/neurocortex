"""Study week boundaries (Monday–Sunday) in configured timezone."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import get_settings


def study_timezone() -> ZoneInfo:
    return ZoneInfo(get_settings().study_timezone)


def week_bounds_for(reference: date | None = None) -> tuple[date, date]:
    tz = study_timezone()
    if reference is None:
        reference = datetime.now(tz).date()
    monday = reference - timedelta(days=reference.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def weekly_session_target(study_frequency: str | None) -> int | None:
    if not study_frequency:
        return None
    mapping = {
        "daily": 7,
        "four_times_weekly": 4,
        "twice_weekly": 2,
        "weekly": 1,
    }
    return mapping.get(study_frequency.strip())

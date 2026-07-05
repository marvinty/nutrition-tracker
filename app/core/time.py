"""Timezone helpers.

Timestamps are stored tz-aware (UTC) in the DB, but "which day" a meal belongs to
and the times shown to the user are computed in a fixed local timezone
(``settings.app_timezone``, default ``Europe/Berlin``). Centralising this here keeps a
later move to per-user timezones a one-spot change.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from app.core.config import settings


def local_tz() -> ZoneInfo:
    return ZoneInfo(settings.app_timezone)


def today_local() -> date:
    """Current calendar date in the configured local timezone."""
    return datetime.now(local_tz()).date()


def day_bounds(d: date) -> tuple[datetime, datetime]:
    """UTC bounds of the local calendar day ``d`` as a half-open interval [start, end).

    Using a half-open interval (rather than ``... 23:59:59``) covers the final second
    and stays correct across DST transitions.
    """
    tz = local_tz()
    start_local = datetime(d.year, d.month, d.day, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def resolve_timestamp(log_date: Optional[date]) -> Optional[datetime]:
    """Timestamp to store for a meal logged against ``log_date``.

    Returns ``None`` for today/unspecified so the DB ``func.now()`` default applies.
    For a past date, keeps the current local time-of-day but on the chosen day.
    Raises ``ValueError`` for future dates.
    """
    if log_date is None:
        return None
    today = today_local()
    if log_date > today:
        raise ValueError("log_date must not be in the future")
    if log_date == today:
        return None
    now = datetime.now(local_tz())
    local_dt = datetime.combine(log_date, now.timetz())  # chosen day, current local time
    return local_dt.astimezone(timezone.utc)  # store UTC, like func.now()


def to_local(dt: datetime) -> datetime:
    """Convert a stored timestamp to local time for display.

    SQLite may hand back naive datetimes; treat those as UTC.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(local_tz())

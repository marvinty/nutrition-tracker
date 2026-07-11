"""German date formatting.

Python's ``strftime`` emits English month/weekday names under the default C locale,
which would break the German UI. These helpers format dates with hard-coded German
names so output is locale-independent and deterministic.
"""

from datetime import date

WEEKDAYS_SHORT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
WEEKDAYS_LONG = [
    "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag",
]
MONTHS_LONG = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]
MONTHS_SHORT = [
    "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
    "Jul", "Aug", "Sep", "Okt", "Nov", "Dez",
]


def format_long(d: date) -> str:
    """e.g. ``Sonntag, 6. Juli 2026``."""
    return f"{WEEKDAYS_LONG[d.weekday()]}, {d.day}. {MONTHS_LONG[d.month - 1]} {d.year}"


def format_month_year(d: date) -> str:
    """e.g. ``Juli 2026``."""
    return f"{MONTHS_LONG[d.month - 1]} {d.year}"


def format_day_month(d: date, *, with_year: bool = False) -> str:
    """e.g. ``6. Jul`` (or ``6. Jul 2026`` with ``with_year``)."""
    base = f"{d.day}. {MONTHS_SHORT[d.month - 1]}"
    return f"{base} {d.year}" if with_year else base


def format_short_weekday(d: date) -> str:
    """e.g. ``Mo, 30. Jun``."""
    return f"{WEEKDAYS_SHORT[d.weekday()]}, {d.day}. {MONTHS_SHORT[d.month - 1]}"

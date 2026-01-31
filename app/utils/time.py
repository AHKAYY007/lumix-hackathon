"""
Time utility functions.
"""

from datetime import datetime, date, timezone
from typing import Optional


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def date_to_datetime(d: date, hour: int = 0, minute: int = 0) -> datetime:
    """Convert date to datetime at specified time."""
    return datetime.combine(d, datetime.min.time().replace(hour=hour, minute=minute))


def datetime_to_date(dt: datetime) -> date:
    """Extract date from datetime."""
    return dt.date()


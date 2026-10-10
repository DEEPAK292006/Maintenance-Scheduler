"""
Date utilities for the Maintenance Scheduler system.

Provides robust date parsing, validation, and interval arithmetic using standard
library `datetime.date` and `datetime.timedelta`.
"""

from datetime import date, timedelta
from typing import Tuple


def parse_date(date_str: str) -> date:
    """Parse a date string in strict YYYY-MM-DD format.

    Args:
        date_str: Date string to validate and parse (e.g., '2026-10-09').

    Returns:
        datetime.date instance.

    Raises:
        ValueError: If the string is malformed, not YYYY-MM-DD, or an invalid calendar date.
    """
    if not isinstance(date_str, str):
        raise ValueError(f"Expected date string, got {type(date_str).__name__}")

    stripped = date_str.strip()
    parts = stripped.split("-")
    if len(parts) != 3:
        raise ValueError(f"Date '{date_str}' does not match required YYYY-MM-DD format.")

    year_str, month_str, day_str = parts
    if len(year_str) != 4 or len(month_str) != 2 or len(day_str) != 2:
        raise ValueError(f"Date '{date_str}' must have 4-digit year, 2-digit month, and 2-digit day (YYYY-MM-DD).")

    try:
        year = int(year_str)
        month = int(month_str)
        day = int(day_str)
    except ValueError as exc:
        raise ValueError(f"Non-numeric component found in date '{date_str}'.") from exc

    try:
        return date(year, month, day)
    except ValueError as exc:
        raise ValueError(f"Invalid calendar date '{date_str}': {exc}") from exc


def format_date(d: date) -> str:
    """Format a date object as an ISO-8601 string 'YYYY-MM-DD'."""
    return d.strftime("%Y-%m-%d")


def calculate_next_due_date(last_service_date: date, interval_days: int) -> date:
    """Calculate the next scheduled service date.

    Formula:
        next_due_date = last_service_date + interval_days

    Args:
        last_service_date: The date when the asset was last serviced.
        interval_days: Service interval in days (must be > 0).

    Returns:
        The date when the next service is due.

    Raises:
        ValueError: If interval_days is <= 0.
    """
    if interval_days <= 0:
        raise ValueError(f"Service interval must be a positive integer, got {interval_days}")
    return last_service_date + timedelta(days=interval_days)


def calculate_days_overdue(next_due_date: date, today: date) -> int:
    """Calculate the number of days an asset is overdue relative to today.

    Rules:
    - An asset is overdue when next_due_date is strictly earlier than today.
    - An asset due today or in the future has 0 days overdue.
    - For an overdue asset:
        days_overdue = (today - next_due_date).days

    Args:
        next_due_date: Scheduled maintenance due date.
        today: Reference current date.

    Returns:
        Positive number of days overdue, or 0 if not overdue.
    """
    if next_due_date < today:
        return (today - next_due_date).days
    return 0


def calculate_days_remaining(next_due_date: date, today: date) -> int:
    """Calculate the signed number of days until the next service date.

    Args:
        next_due_date: Scheduled maintenance due date.
        today: Reference current date.

    Returns:
        (next_due_date - today).days:
        - Positive: due in the future
        - Zero: due today
        - Negative: overdue
    """
    return (next_due_date - today).days


def is_overdue(next_due_date: date, today: date) -> bool:
    """Determine whether an asset is overdue.

    An asset is overdue if its next_due_date is strictly before today.
    An asset due today is classified as due today, NOT overdue.
    """
    return next_due_date < today


def is_due_today(next_due_date: date, today: date) -> bool:
    """Determine whether an asset's next service is due today."""
    return next_due_date == today


def is_due_within(next_due_date: date, today: date, window_days: int = 30) -> bool:
    """Determine whether an asset is due between today and window_days from today, inclusive.

    Overdue assets (due prior to today) return False.

    Args:
        next_due_date: The due date to evaluate.
        today: Reference current date.
        window_days: Positive lookahead window in days (default 30).

    Returns:
        True if 0 <= (next_due_date - today).days <= window_days, False otherwise.
    """
    if window_days < 0:
        raise ValueError(f"window_days cannot be negative, got {window_days}")
    days_left = (next_due_date - today).days
    return 0 <= days_left <= window_days


def compare_dates(d1: date, d2: date) -> int:
    """Compare two dates.

    Returns:
        -1 if d1 < d2, 0 if d1 == d2, 1 if d1 > d2.
    """
    if d1 < d2:
        return -1
    elif d1 > d2:
        return 1
    return 0

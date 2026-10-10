"""
Unit tests for date_utils.py.
"""

from datetime import date
from pathlib import Path
import sys
import unittest

# Ensure parent directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from date_utils import (
    calculate_days_overdue,
    calculate_days_remaining,
    calculate_next_due_date,
    compare_dates,
    format_date,
    is_due_today,
    is_due_within,
    is_overdue,
    parse_date,
)


class TestDateUtils(unittest.TestCase):
    """Test suite verifying all date utility calculations and edge cases."""

    def test_parse_date_valid(self) -> None:
        """Valid YYYY-MM-DD date strings parse correctly."""
        self.assertEqual(parse_date("2026-10-09"), date(2026, 10, 9))
        self.assertEqual(parse_date("2024-02-29"), date(2024, 2, 29))  # Leap year
        self.assertEqual(parse_date("2000-01-01"), date(2000, 1, 1))

    def test_parse_date_invalid(self) -> None:
        """Malformed, out-of-range, and impossible calendar dates must raise ValueError."""
        invalid_cases = [
            "2026-02-29",  # 2026 is not a leap year
            "2026-13-01",  # Invalid month
            "2026-04-31",  # April only has 30 days
            "26-10-09",    # 2-digit year
            "2026/10/09",  # Slash separator
            "10-09-2026",  # MM-DD-YYYY format
            "not-a-date",
            "",
            "   ",
            "2026-00-10",
            "2026-05-00",
        ]
        for item in invalid_cases:
            with self.subTest(date_str=item):
                with self.assertRaises(ValueError):
                    parse_date(item)

    def test_format_date(self) -> None:
        """Date formatting produces correct ISO string."""
        self.assertEqual(format_date(date(2026, 10, 9)), "2026-10-09")
        self.assertEqual(format_date(date(2024, 2, 29)), "2024-02-29")

    def test_next_due_date_calculation(self) -> None:
        """Calculates next due date properly across intervals."""
        # Sample dataset case: 2026-03-01 + 180 days = 2026-08-28
        last_service = date(2026, 3, 1)
        self.assertEqual(calculate_next_due_date(last_service, 180), date(2026, 8, 28))

        # Sample dataset case: 2026-08-01 + 90 days = 2026-10-30
        self.assertEqual(calculate_next_due_date(date(2026, 8, 1), 90), date(2026, 10, 30))

        # Sample dataset case: 2026-01-15 + 365 days = 2027-01-15
        self.assertEqual(calculate_next_due_date(date(2026, 1, 15), 365), date(2027, 1, 15))

    def test_next_due_date_invalid_interval(self) -> None:
        """Non-positive intervals must raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_next_due_date(date(2026, 1, 1), 0)
        with self.assertRaises(ValueError):
            calculate_next_due_date(date(2026, 1, 1), -10)

    def test_month_and_year_boundaries(self) -> None:
        """Handles month end and year boundary rollovers."""
        # Month rollover
        self.assertEqual(calculate_next_due_date(date(2026, 1, 31), 1), date(2026, 2, 1))
        # Year rollover
        self.assertEqual(calculate_next_due_date(date(2026, 12, 31), 1), date(2027, 1, 1))
        self.assertEqual(calculate_next_due_date(date(2026, 12, 1), 31), date(2027, 1, 1))

    def test_leap_year_arithmetic(self) -> None:
        """Verifies correct day counts through leap-year February."""
        leap_start = date(2024, 2, 28)
        self.assertEqual(calculate_next_due_date(leap_start, 1), date(2024, 2, 29))
        self.assertEqual(calculate_next_due_date(leap_start, 2), date(2024, 3, 1))

        non_leap_start = date(2025, 2, 28)
        self.assertEqual(calculate_next_due_date(non_leap_start, 1), date(2025, 3, 1))

    def test_overdue_calculations(self) -> None:
        """Verifies days overdue and overdue detection."""
        today = date(2026, 10, 9)

        # Overdue asset (A101 in sample): due 2026-08-28 -> 42 days overdue
        due_a101 = date(2026, 8, 28)
        self.assertTrue(is_overdue(due_a101, today))
        self.assertEqual(calculate_days_overdue(due_a101, today), 42)
        self.assertEqual(calculate_days_remaining(due_a101, today), -42)

        # Asset due yesterday
        due_yesterday = date(2026, 10, 8)
        self.assertTrue(is_overdue(due_yesterday, today))
        self.assertEqual(calculate_days_overdue(due_yesterday, today), 1)
        self.assertEqual(calculate_days_remaining(due_yesterday, today), -1)

    def test_due_today(self) -> None:
        """An asset due today must be classified as due today, NOT overdue."""
        today = date(2026, 10, 9)
        due_today = date(2026, 10, 9)

        self.assertFalse(is_overdue(due_today, today))
        self.assertTrue(is_due_today(due_today, today))
        self.assertEqual(calculate_days_overdue(due_today, today), 0)
        self.assertEqual(calculate_days_remaining(due_today, today), 0)

    def test_future_due_asset(self) -> None:
        """Assets due in the future are not overdue."""
        today = date(2026, 10, 9)
        future_due = date(2026, 10, 30)

        self.assertFalse(is_overdue(future_due, today))
        self.assertFalse(is_due_today(future_due, today))
        self.assertEqual(calculate_days_overdue(future_due, today), 0)
        self.assertEqual(calculate_days_remaining(future_due, today), 21)

    def test_due_within_30_days_boundaries(self) -> None:
        """Tests the [0, 30] day inclusion window."""
        today = date(2026, 10, 9)

        # Due today (0 days) -> INCLUDED
        self.assertTrue(is_due_within(date(2026, 10, 9), today, 30))

        # Due tomorrow (1 day) -> INCLUDED
        self.assertTrue(is_due_within(date(2026, 10, 10), today, 30))

        # Due in exactly 30 days -> INCLUDED (2026-11-08)
        self.assertTrue(is_due_within(date(2026, 11, 8), today, 30))

        # Due in 31 days -> EXCLUDED (2026-11-09)
        self.assertFalse(is_due_within(date(2026, 11, 9), today, 30))

        # Overdue by 1 day -> EXCLUDED
        self.assertFalse(is_due_within(date(2026, 10, 8), today, 30))

        # Negative window_days raises ValueError
        with self.assertRaises(ValueError):
            is_due_within(date(2026, 10, 15), today, -1)

    def test_compare_dates(self) -> None:
        """Compare dates utility."""
        d1 = date(2026, 1, 1)
        d2 = date(2026, 1, 2)
        self.assertEqual(compare_dates(d1, d2), -1)
        self.assertEqual(compare_dates(d2, d1), 1)
        self.assertEqual(compare_dates(d1, d1), 0)


if __name__ == "__main__":
    unittest.main()

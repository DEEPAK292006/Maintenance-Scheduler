"""
Unit tests for input_handler.py.
"""

from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from input_handler import InputHandler, InputValidationError


class TestInputValidation(unittest.TestCase):
    """Test suite verifying strict input parsing and specific error reporting."""

    def test_valid_sample_input(self) -> None:
        """Correctly parses valid 3-asset dataset."""
        lines = [
            "2026-10-09",
            "3",
            "A101 180 2026-03-01 1",
            "A102 90 2026-08-01 3",
            "A103 365 2026-01-15 0",
        ]
        today, assets = InputHandler.parse_lines(lines)

        self.assertEqual(today, date(2026, 10, 9))
        self.assertEqual(len(assets), 3)
        self.assertEqual(assets[0].asset_id, "A101")
        self.assertEqual(assets[1].asset_id, "A102")
        self.assertEqual(assets[2].asset_id, "A103")

    def test_empty_input(self) -> None:
        """Empty input raises InputValidationError."""
        with self.assertRaises(InputValidationError) as ctx:
            InputHandler.parse_lines([])
        self.assertIn("empty", str(ctx.exception).lower())

    def test_invalid_today_date(self) -> None:
        """Malformed date on line 1 raises InputValidationError."""
        lines = ["2026-13-99", "1", "A1 10 2026-01-01 0"]
        with self.assertRaises(InputValidationError) as ctx:
            InputHandler.parse_lines(lines)
        self.assertIn("Line 1", str(ctx.exception))

    def test_invalid_asset_count_n(self) -> None:
        """Non-numeric or negative n on line 2 raises error."""
        with self.assertRaises(InputValidationError) as ctx:
            InputHandler.parse_lines(["2026-10-09", "three", "A1 10 2026-01-01 0"])
        self.assertIn("Line 2", str(ctx.exception))

        with self.assertRaises(InputValidationError) as ctx:
            InputHandler.parse_lines(["2026-10-09", "-5"])
        self.assertIn("Line 2", str(ctx.exception))

    def test_missing_fields_in_record(self) -> None:
        """Record with fewer than 4 tokens raises error."""
        lines = [
            "2026-10-09",
            "1",
            "A101 180 2026-03-01",  # missing repair count
        ]
        with self.assertRaises(InputValidationError) as ctx:
            InputHandler.parse_lines(lines)
        self.assertIn("Expected 4 fields", str(ctx.exception))

    def test_extra_fields_in_record(self) -> None:
        """Record with more than 4 tokens raises error."""
        lines = [
            "2026-10-09",
            "1",
            "A101 180 2026-03-01 1 EXTRA_FIELD",
        ]
        with self.assertRaises(InputValidationError) as ctx:
            InputHandler.parse_lines(lines)
        self.assertIn("Expected 4 fields", str(ctx.exception))

    def test_non_positive_service_interval(self) -> None:
        """Zero or negative service intervals raise error."""
        lines_zero = ["2026-10-09", "1", "A101 0 2026-03-01 1"]
        with self.assertRaises(InputValidationError) as ctx:
            InputHandler.parse_lines(lines_zero)
        self.assertIn("service interval", str(ctx.exception).lower())

        lines_neg = ["2026-10-09", "1", "A101 -30 2026-03-01 1"]
        with self.assertRaises(InputValidationError) as ctx:
            InputHandler.parse_lines(lines_neg)
        self.assertIn("service interval", str(ctx.exception).lower())

    def test_negative_repair_count(self) -> None:
        """Negative historical repairs raise error."""
        lines = ["2026-10-09", "1", "A101 90 2026-03-01 -2"]
        with self.assertRaises(InputValidationError) as ctx:
            InputHandler.parse_lines(lines)
        self.assertIn("repair count", str(ctx.exception).lower())

    def test_duplicate_asset_id(self) -> None:
        """Duplicate asset IDs are rejected with specific error."""
        lines = [
            "2026-10-09",
            "2",
            "A101 90 2026-03-01 1",
            "A101 180 2026-05-01 0",
        ]
        with self.assertRaises(InputValidationError) as ctx:
            InputHandler.parse_lines(lines)
        self.assertIn("Duplicate asset ID 'A101'", str(ctx.exception))

    def test_premature_eof(self) -> None:
        """Input with fewer records than specified by n raises error."""
        lines = [
            "2026-10-09",
            "5",  # Expects 5, only 1 provided
            "A101 90 2026-03-01 1",
        ]
        with self.assertRaises(InputValidationError) as ctx:
            InputHandler.parse_lines(lines)
        self.assertIn("Premature EOF", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

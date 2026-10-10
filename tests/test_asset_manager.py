"""
Unit tests for models.py and asset_manager.py.
"""

from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from asset_manager import AssetManager
from models import Asset


class TestAssetManager(unittest.TestCase):
    """Test suite verifying Asset model logic and AssetManager operations."""

    def setUp(self) -> None:
        self.today = date(2026, 10, 9)
        # Sample items
        self.a101 = Asset("A101", 180, date(2026, 3, 1), 1)   # Due 2026-08-28 (Overdue by 42d)
        self.a102 = Asset("A102", 90, date(2026, 8, 1), 3)    # Due 2026-10-30 (Due in 21d, Replace=True)
        self.a103 = Asset("A103", 365, date(2026, 1, 15), 0)  # Due 2027-01-15 (Due in 98d, Replace=False)

    def test_asset_model_instantiation(self) -> None:
        """Asset stores attributes and computes next_due_date accurately."""
        self.assertEqual(self.a101.asset_id, "A101")
        self.assertEqual(self.a101.interval_days, 180)
        self.assertEqual(self.a101.last_service_date, date(2026, 3, 1))
        self.assertEqual(self.a101.repairs, 1)
        self.assertEqual(self.a101.next_due_date, date(2026, 8, 28))

    def test_asset_invalid_instantiation(self) -> None:
        """Invalid asset inputs reject with ValueError."""
        # Empty ID
        with self.assertRaises(ValueError):
            Asset("", 90, date(2026, 1, 1), 0)
        # Non-positive interval
        with self.assertRaises(ValueError):
            Asset("A1", 0, date(2026, 1, 1), 0)
        with self.assertRaises(ValueError):
            Asset("A1", -5, date(2026, 1, 1), 0)
        # Negative repairs
        with self.assertRaises(ValueError):
            Asset("A1", 90, date(2026, 1, 1), -1)

    def test_overdue_detection(self) -> None:
        """Verifies identification and deterministic ordering of overdue assets."""
        assets = [self.a102, self.a101, self.a103]
        overdue = AssetManager.get_overdue_assets(assets, self.today)

        self.assertEqual(len(overdue), 1)
        self.assertEqual(overdue[0].asset_id, "A101")
        self.assertEqual(overdue[0].days_overdue(self.today), 42)

    def test_overdue_deterministic_tie_breaking(self) -> None:
        """Two assets with identical overdue due dates are sorted alphabetically by asset_id."""
        asset_z = Asset("Z999", 30, date(2026, 8, 1), 0)  # Due 2026-08-31
        asset_a = Asset("A001", 30, date(2026, 8, 1), 0)  # Due 2026-08-31
        asset_m = Asset("M500", 30, date(2026, 8, 1), 0)  # Due 2026-08-31

        overdue = AssetManager.get_overdue_assets([asset_z, asset_a, asset_m], self.today)
        self.assertEqual([a.asset_id for a in overdue], ["A001", "M500", "Z999"])

    def test_upcoming_assets_due_in_30_days(self) -> None:
        """Finds assets due within next 30 days, excluding overdue and far-future assets."""
        assets = [self.a101, self.a102, self.a103]
        upcoming = AssetManager.get_upcoming_assets(assets, self.today, window_days=30)

        # A101 is overdue -> excluded
        # A102 is due in 21 days -> included
        # A103 is due in 98 days -> excluded
        self.assertEqual(len(upcoming), 1)
        self.assertEqual(upcoming[0].asset_id, "A102")
        self.assertEqual(upcoming[0].days_remaining(self.today), 21)

    def test_replacement_threshold(self) -> None:
        """Flags assets meeting replacement criteria."""
        assets = [self.a101, self.a102, self.a103]
        replacements = AssetManager.get_replacement_assets(assets, threshold=3)

        self.assertEqual(len(replacements), 1)
        self.assertEqual(replacements[0].asset_id, "A102")

    def test_empty_asset_list(self) -> None:
        """Handles empty asset list gracefully without errors."""
        self.assertEqual(AssetManager.get_overdue_assets([], self.today), [])
        self.assertEqual(AssetManager.get_upcoming_assets([], self.today), [])
        self.assertEqual(AssetManager.get_replacement_assets([], threshold=3), [])


if __name__ == "__main__":
    unittest.main()

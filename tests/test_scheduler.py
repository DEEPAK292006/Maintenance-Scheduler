"""
Unit tests for scheduler.py.
"""

from datetime import date, timedelta
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import Asset
from scheduler import MaintenanceScheduler


class TestMaintenanceScheduler(unittest.TestCase):
    """Test suite verifying capacity constraints, EDF ordering, lateness metrics, and edge cases."""

    def setUp(self) -> None:
        self.today = date(2026, 10, 9)

    def test_invalid_capacity(self) -> None:
        """Non-positive capacity raises ValueError."""
        with self.assertRaises(ValueError):
            MaintenanceScheduler(daily_capacity=0)
        with self.assertRaises(ValueError):
            MaintenanceScheduler(daily_capacity=-3)

    def test_invalid_horizon(self) -> None:
        """Negative horizon raises ValueError."""
        with self.assertRaises(ValueError):
            MaintenanceScheduler(daily_capacity=5, horizon_days=-10)

    def test_edf_ordering_with_capacity(self) -> None:
        """Assets are scheduled in Earliest Deadline First order, capped by daily capacity."""
        # Create assets with different due dates:
        # A1: Due 2026-10-10
        # A2: Due 2026-10-09 (today)
        # A3: Due 2026-10-08 (overdue by 1 day)
        # A4: Due 2026-10-12
        a1 = Asset("A1", 10, date(2026, 9, 30), 0)  # Due 2026-10-10
        a2 = Asset("A2", 9, date(2026, 9, 30), 0)   # Due 2026-10-09
        a3 = Asset("A3", 8, date(2026, 9, 30), 0)   # Due 2026-10-08 (overdue)
        a4 = Asset("A4", 12, date(2026, 9, 30), 0)  # Due 2026-10-12

        # Daily capacity = 1
        scheduler = MaintenanceScheduler(daily_capacity=1, horizon_days=30)
        result = scheduler.schedule([a1, a2, a3, a4], self.today)

        self.assertEqual(result.total_scheduled, 4)
        # Earliest due is A3 (2026-10-08, overdue) -> target is today (2026-10-09) -> scheduled 2026-10-09
        self.assertEqual(result.services[0].asset.asset_id, "A3")
        self.assertEqual(result.services[0].scheduled_date, self.today)
        self.assertEqual(result.services[0].lateness, 1)

        # Next due is A2 (due 2026-10-09) -> target is 2026-10-09, but day full, rolls to 2026-10-10
        self.assertEqual(result.services[1].asset.asset_id, "A2")
        self.assertEqual(result.services[1].scheduled_date, date(2026, 10, 10))
        self.assertEqual(result.services[1].lateness, 1)

        # Next due is A1 (due 2026-10-10) -> rolls to 2026-10-11
        self.assertEqual(result.services[2].asset.asset_id, "A1")
        self.assertEqual(result.services[2].scheduled_date, date(2026, 10, 11))
        self.assertEqual(result.services[2].lateness, 1)

        # Next due is A4 (due 2026-10-12) -> scheduled 2026-10-12 (on time!)
        self.assertEqual(result.services[3].asset.asset_id, "A4")
        self.assertEqual(result.services[3].scheduled_date, date(2026, 10, 12))
        self.assertEqual(result.services[3].lateness, 0)

    def test_daily_capacity_enforcement(self) -> None:
        """Capacity = 2 allows exactly 2 assets per day."""
        assets = [
            Asset(f"DEV_{i}", 1, date(2026, 10, 8), 0)  # All due 2026-10-09 (today)
            for i in range(5)
        ]

        scheduler = MaintenanceScheduler(daily_capacity=2, horizon_days=30)
        result = scheduler.schedule(assets, self.today)

        # 5 assets:
        # Day 0 (2026-10-09): 2 assets
        # Day 1 (2026-10-10): 2 assets
        # Day 2 (2026-10-11): 1 asset
        self.assertEqual(len(result.daily_schedule[date(2026, 10, 9)]), 2)
        self.assertEqual(len(result.daily_schedule[date(2026, 10, 10)]), 2)
        self.assertEqual(len(result.daily_schedule[date(2026, 10, 11)]), 1)
        self.assertEqual(result.total_scheduled, 5)

    def test_deterministic_tie_breaking(self) -> None:
        """When due dates are identical, assets are processed alphabetically by asset_id."""
        assets = [
            Asset("ZEBRA", 10, date(2026, 10, 1), 0),
            Asset("ALPHA", 10, date(2026, 10, 1), 0),
            Asset("BETA", 10, date(2026, 10, 1), 0),
        ]
        scheduler = MaintenanceScheduler(daily_capacity=1, horizon_days=30)
        result = scheduler.schedule(assets, self.today)

        scheduled_order = [s.asset.asset_id for s in result.services]
        self.assertEqual(scheduled_order, ["ALPHA", "BETA", "ZEBRA"])

    def test_all_overdue_assets(self) -> None:
        """Scheduling when all assets are already overdue."""
        assets = [
            Asset("OV1", 10, date(2026, 9, 1), 0),  # Due 2026-09-11 (overdue 28d)
            Asset("OV2", 10, date(2026, 9, 5), 0),  # Due 2026-09-15 (overdue 24d)
            Asset("OV3", 10, date(2026, 9, 10), 0), # Due 2026-09-20 (overdue 19d)
        ]
        scheduler = MaintenanceScheduler(daily_capacity=2, horizon_days=30)
        result = scheduler.schedule(assets, self.today)

        self.assertEqual(result.overdue_count, 3)
        self.assertEqual(result.total_scheduled, 3)
        self.assertGreater(result.total_lateness, 0)
        self.assertGreater(result.max_lateness, 0)
        # Services start on today (2026-10-09)
        self.assertEqual(result.services[0].scheduled_date, self.today)
        self.assertEqual(result.services[1].scheduled_date, self.today)
        self.assertEqual(result.services[2].scheduled_date, self.today + timedelta(days=1))

    def test_horizon_filtering(self) -> None:
        """Assets due beyond the configured horizon are omitted from current schedule."""
        a_near = Asset("NEAR", 10, self.today, 0)   # Due today + 10d
        a_far = Asset("FAR", 100, self.today, 0)    # Due today + 100d

        # Horizon = 30 days
        scheduler = MaintenanceScheduler(daily_capacity=5, horizon_days=30)
        result = scheduler.schedule([a_near, a_far], self.today)

        scheduled_ids = [s.asset.asset_id for s in result.services]
        self.assertIn("NEAR", scheduled_ids)
        self.assertNotIn("FAR", scheduled_ids)

        # Unbounded horizon (horizon_days=None)
        scheduler_all = MaintenanceScheduler(daily_capacity=5, horizon_days=None)
        result_all = scheduler_all.schedule([a_near, a_far], self.today)
        all_ids = [s.asset.asset_id for s in result_all.services]
        self.assertIn("NEAR", all_ids)
        self.assertIn("FAR", all_ids)

    def test_empty_input(self) -> None:
        """Empty asset list produces clean empty schedule without error."""
        scheduler = MaintenanceScheduler(daily_capacity=5, horizon_days=30)
        result = scheduler.schedule([], self.today)
        self.assertEqual(result.total_scheduled, 0)
        self.assertEqual(result.total_lateness, 0)
        self.assertEqual(result.max_lateness, 0)
        self.assertEqual(len(result.services), 0)


if __name__ == "__main__":
    unittest.main()

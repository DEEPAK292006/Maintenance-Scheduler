"""
Unit tests for replacement_analyzer.py.
"""

from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import Asset
from replacement_analyzer import ReplacementAnalyzer


class TestReplacementAnalyzer(unittest.TestCase):
    """Test suite verifying replacement threshold detection, failure-rate proxies, and urgency rankings."""

    def setUp(self) -> None:
        self.today = date(2026, 10, 9)

    def test_replacement_threshold_behavior(self) -> None:
        """Verifies threshold boundary logic for 2, 3, and 4 repairs."""
        a_2 = Asset("R2", 90, date(2026, 7, 1), 2)
        a_3 = Asset("R3", 90, date(2026, 7, 1), 3)
        a_4 = Asset("R4", 90, date(2026, 7, 1), 4)

        # Default threshold = 3
        cands = ReplacementAnalyzer.analyze([a_2, a_3, a_4], self.today, threshold=3)
        cand_ids = {c.asset.asset_id for c in cands}
        self.assertNotIn("R2", cand_ids)
        self.assertIn("R3", cand_ids)
        self.assertIn("R4", cand_ids)

        # Custom threshold = 2
        cands_t2 = ReplacementAnalyzer.analyze([a_2, a_3, a_4], self.today, threshold=2)
        cand_ids_t2 = {c.asset.asset_id for c in cands_t2}
        self.assertIn("R2", cand_ids_t2)

        # Custom threshold = 4
        cands_t4 = ReplacementAnalyzer.analyze([a_2, a_3, a_4], self.today, threshold=4)
        cand_ids_t4 = {c.asset.asset_id for c in cands_t4}
        self.assertNotIn("R2", cand_ids_t4)
        self.assertNotIn("R3", cand_ids_t4)
        self.assertIn("R4", cand_ids_t4)

    def test_sample_case_failure_rate(self) -> None:
        """Verifies failure rate arithmetic for sample asset A102."""
        # A102: last_service=2026-08-01, today=2026-10-09, repairs=3
        # observation_days = (2026-10-09 - 2026-08-01).days = 69 days
        # failure_rate = 3 / (69 / 365) = 15.86956...
        a102 = Asset("A102", 90, date(2026, 8, 1), 3)
        cands = ReplacementAnalyzer.analyze([a102], self.today, threshold=3, min_observation_days=30)

        self.assertEqual(len(cands), 1)
        cand = cands[0]
        self.assertAlmostEqual(cand.failure_rate, 3.0 / (69.0 / 365.0), places=3)
        self.assertFalse(cand.is_overdue)
        self.assertEqual(cand.days_overdue, 0)
        # Urgency score when not overdue = failure_rate * 1.0 + 0 = failure_rate
        self.assertAlmostEqual(cand.urgency_score, cand.failure_rate, places=3)

    def test_min_observation_window_clamping(self) -> None:
        """Prevents division by zero or unstable rates for services performed today."""
        # Asset serviced today with 3 repairs
        a_recent = Asset("REC", 90, self.today, 3)
        # Elapsed days = 0, clamped to min_observation_days = 30
        cands = ReplacementAnalyzer.analyze([a_recent], self.today, threshold=3, min_observation_days=30)
        expected_rate = 3.0 / (30.0 / 365.0)
        self.assertAlmostEqual(cands[0].failure_rate, expected_rate, places=3)

    def test_urgency_ranking_order(self) -> None:
        """Assets with higher urgency scores (high failure rate and overdue) rank first."""
        # Asset 1: 5 repairs, last serviced 60 days ago, currently overdue by 30 days
        a_critical = Asset("CRIT", 30, date(2026, 8, 10), 5)
        # Asset 2: 3 repairs, last serviced 180 days ago, not overdue
        a_moderate = Asset("MOD", 365, date(2026, 4, 10), 3)

        cands = ReplacementAnalyzer.analyze([a_moderate, a_critical], self.today, threshold=3)
        self.assertEqual(len(cands), 2)
        self.assertEqual(cands[0].asset.asset_id, "CRIT")
        self.assertEqual(cands[1].asset.asset_id, "MOD")
        self.assertGreater(cands[0].urgency_score, cands[1].urgency_score)

    def test_deterministic_tie_breaking(self) -> None:
        """Deterministic tie-breaking by due_date, then asset_id."""
        a1 = Asset("B_SAME", 90, date(2026, 7, 1), 3)
        a2 = Asset("A_SAME", 90, date(2026, 7, 1), 3)

        cands = ReplacementAnalyzer.analyze([a1, a2], self.today, threshold=3)
        self.assertEqual([c.asset.asset_id for c in cands], ["A_SAME", "B_SAME"])


if __name__ == "__main__":
    unittest.main()

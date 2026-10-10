"""
Asset management and query services for maintenance scheduling.

Coordinates filtering, sorting, and classification of assets into overdue,
upcoming, and replacement categories.
"""

from datetime import date
from typing import Iterable, List
try:
    from .models import Asset
except ImportError:
    from models import Asset


class AssetManager:
    """Manages collections of assets and performs core filtering/sorting operations."""

    @staticmethod
    def get_overdue_assets(assets: Iterable[Asset], today: date) -> List[Asset]:
        """Identify all assets whose next service date is earlier than today.

        Results are deterministically sorted by earliest due date, breaking ties
        by asset_id.

        Args:
            assets: Iterable of Asset objects.
            today: Reference current date.

        Returns:
            List of overdue Asset objects sorted by (next_due_date, asset_id).
        """
        overdue = [a for a in assets if a.is_overdue(today)]
        # Asset implements __lt__ sorting by (next_due_date, asset_id)
        overdue.sort()
        return overdue

    @staticmethod
    def get_upcoming_assets(
        assets: Iterable[Asset],
        today: date,
        window_days: int = 30,
    ) -> List[Asset]:
        """Identify assets due between today and window_days from today, inclusive.

        Overdue assets are excluded.
        Results are deterministically sorted by earliest due date, breaking ties
        by asset_id.

        Args:
            assets: Iterable of Asset objects.
            today: Reference current date.
            window_days: Lookahead window in days (default 30).

        Returns:
            List of upcoming Asset objects sorted by (next_due_date, asset_id).
        """
        upcoming = [a for a in assets if a.is_due_within(today, window_days)]
        upcoming.sort()
        return upcoming

    @staticmethod
    def get_replacement_assets(
        assets: Iterable[Asset],
        threshold: int = 3,
    ) -> List[Asset]:
        """Filter assets that have accumulated at least the threshold number of repairs.

        Args:
            assets: Iterable of Asset objects.
            threshold: Minimum historical repair count (default 3).

        Returns:
            List of Asset objects meeting or exceeding the threshold.
        """
        return [a for a in assets if a.is_replacement_candidate(threshold)]

"""
Data models for assets, service records, and schedules.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional
try:
    from .date_utils import (
        calculate_days_overdue,
        calculate_days_remaining,
        calculate_next_due_date,
        is_due_today,
        is_due_within,
        is_overdue,
    )
except ImportError:
    from date_utils import (
        calculate_days_overdue,
        calculate_days_remaining,
        calculate_next_due_date,
        is_due_today,
        is_due_within,
        is_overdue,
    )


class Asset:
    """Represents an equipment asset tracked by the maintenance system.

    Attributes:
        asset_id: Unique string identifier for the asset.
        interval_days: Mandatory operating interval (in days) between services.
        last_service_date: Calendar date of the most recent service.
        repairs: Historical count of repairs/breakdowns recorded.
    """

    __slots__ = ("_asset_id", "_interval_days", "_last_service_date", "_repairs", "_next_due_date")

    def __init__(
        self,
        asset_id: str,
        interval_days: int,
        last_service_date: date,
        repairs: int,
    ) -> None:
        if not asset_id or not asset_id.strip():
            raise ValueError("Asset ID cannot be empty.")
        if interval_days <= 0:
            raise ValueError(f"Service interval must be positive (> 0), got {interval_days}")
        if repairs < 0:
            raise ValueError(f"Repair count cannot be negative, got {repairs}")
        if not isinstance(last_service_date, date):
            raise ValueError(f"last_service_date must be a datetime.date, got {type(last_service_date)}")

        self._asset_id: str = asset_id.strip()
        self._interval_days: int = interval_days
        self._last_service_date: date = last_service_date
        self._repairs: int = repairs
        # Pre-compute next_due_date once at instantiation since last_service_date and interval_days are immutable.
        self._next_due_date: date = calculate_next_due_date(last_service_date, interval_days)

    @property
    def asset_id(self) -> str:
        return self._asset_id

    @property
    def interval_days(self) -> int:
        return self._interval_days

    @property
    def last_service_date(self) -> date:
        return self._last_service_date

    @property
    def repairs(self) -> int:
        return self._repairs

    @property
    def next_due_date(self) -> date:
        """The calendar date on which the next preventive service is due."""
        return self._next_due_date

    def days_overdue(self, today: date) -> int:
        """Returns positive days overdue if past due relative to today, else 0."""
        return calculate_days_overdue(self._next_due_date, today)

    def days_remaining(self, today: date) -> int:
        """Returns signed days remaining until due (negative if overdue)."""
        return calculate_days_remaining(self._next_due_date, today)

    def is_overdue(self, today: date) -> bool:
        """True if next_due_date is strictly before today."""
        return is_overdue(self._next_due_date, today)

    def is_due_today(self, today: date) -> bool:
        """True if next_due_date is exactly today."""
        return is_due_today(self._next_due_date, today)

    def is_due_within(self, today: date, window_days: int = 30) -> bool:
        """True if next_due_date falls between today and today + window_days inclusive."""
        return is_due_within(self._next_due_date, today, window_days)

    def is_replacement_candidate(self, threshold: int = 3) -> bool:
        """True if historical repairs meet or exceed the replacement threshold (default >= 3)."""
        return self._repairs >= threshold

    def estimate_failure_rate(self, today: date, min_observation_days: int = 30) -> float:
        """Estimate failure rate as repairs per year.

        Formula:
            observation_period_days = max((today - last_service_date).days, min_observation_days)
            observation_period_years = observation_period_days / 365.0
            failure_rate = repairs / observation_period_years

        Args:
            today: Reference current date.
            min_observation_days: Floor on observation period to avoid division by zero
                or hyper-inflated estimates for recently serviced assets.

        Returns:
            Estimated repairs per year (float).
        """
        elapsed_days = (today - self._last_service_date).days
        observation_days = max(elapsed_days, min_observation_days)
        observation_years = observation_days / 365.0
        return self._repairs / observation_years

    def replacement_urgency_score(self, today: date, min_observation_days: int = 30) -> float:
        """Calculates a transparent urgency score for sorting replacement candidates.

        Urgency Scoring Rule:
            urgency_score = failure_rate * (1.5 if is_overdue else 1.0) + (days_overdue / 30.0)

        High failure rate combined with being overdue yields maximum replacement urgency.
        """
        failure_rate = self.estimate_failure_rate(today, min_observation_days)
        overdue = self.is_overdue(today)
        overdue_days = self.days_overdue(today)
        multiplier = 1.5 if overdue else 1.0
        return (failure_rate * multiplier) + (overdue_days / 30.0)

    def __lt__(self, other: "Asset") -> bool:
        """Deterministic ordering: earliest next_due_date first, tie-break by asset_id."""
        if not isinstance(other, Asset):
            return NotImplemented
        if self._next_due_date != other._next_due_date:
            return self._next_due_date < other._next_due_date
        return self._asset_id < other._asset_id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Asset):
            return NotImplemented
        return self._asset_id == other._asset_id

    def __hash__(self) -> int:
        return hash(self._asset_id)

    def __repr__(self) -> str:
        return (
            f"Asset(id='{self._asset_id}', interval={self._interval_days}, "
            f"last='{self._last_service_date}', repairs={self._repairs}, "
            f"due='{self._next_due_date}')"
        )


@dataclass(frozen=True)
class ScheduledService:
    """Represents a scheduled maintenance appointment for an asset."""

    asset: Asset
    scheduled_date: date
    due_date: date
    lateness: int = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "lateness",
            max(0, (self.scheduled_date - self.due_date).days),
        )


@dataclass
class ScheduleResult:
    """Aggregated outcome of capacity-constrained scheduling execution."""

    services: List[ScheduledService]
    daily_schedule: Dict[date, List[ScheduledService]]
    total_lateness: int
    max_lateness: int
    overdue_count: int
    total_scheduled: int
    daily_capacity: int
    horizon_days: Optional[int]


@dataclass(frozen=True)
class ReplacementCandidate:
    """Detailed review record for an asset flagged for replacement."""

    asset: Asset
    repairs: int
    failure_rate: float
    is_overdue: bool
    days_overdue: int
    urgency_score: float

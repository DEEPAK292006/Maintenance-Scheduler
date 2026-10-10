"""
Configuration settings and default parameters for the Maintenance Scheduler system.
"""

from dataclasses import dataclass


# Global System Defaults
DEFAULT_DAILY_CAPACITY: int = 5
DEFAULT_HORIZON_DAYS: int = 60
REPLACEMENT_REPAIR_THRESHOLD: int = 3
MIN_OBSERVATION_DAYS: int = 30
UPCOMING_WINDOW_DAYS: int = 30
DATE_FORMAT: str = "%Y-%m-%d"


@dataclass(frozen=True)
class SchedulerConfig:
    """Immutable configuration container for runtime parameters.

    Attributes:
        daily_capacity: Maximum number of maintenance services a technician can perform per day.
        horizon_days: Number of days into the future to consider for preventive scheduling.
        replacement_threshold: Minimum historical repair count to trigger replacement review.
        min_observation_days: Floor on observation window to avoid division by zero / volatility.
        upcoming_window_days: Days lookahead for upcoming maintenance report (Feature F).
    """

    daily_capacity: int = DEFAULT_DAILY_CAPACITY
    horizon_days: int = DEFAULT_HORIZON_DAYS
    replacement_threshold: int = REPLACEMENT_REPAIR_THRESHOLD
    min_observation_days: int = MIN_OBSERVATION_DAYS
    upcoming_window_days: int = UPCOMING_WINDOW_DAYS

    def __post_init__(self) -> None:
        if self.daily_capacity <= 0:
            raise ValueError(f"daily_capacity must be a positive integer, got {self.daily_capacity}")
        if self.horizon_days < 0:
            raise ValueError(f"horizon_days cannot be negative, got {self.horizon_days}")
        if self.replacement_threshold < 0:
            raise ValueError(f"replacement_threshold cannot be negative, got {self.replacement_threshold}")
        if self.min_observation_days <= 0:
            raise ValueError(f"min_observation_days must be a positive integer, got {self.min_observation_days}")
        if self.upcoming_window_days < 0:
            raise ValueError(f"upcoming_window_days cannot be negative, got {self.upcoming_window_days}")

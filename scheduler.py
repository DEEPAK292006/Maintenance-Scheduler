"""
Capacity-Constrained Maintenance Scheduler using Earliest Deadline First (EDF).

Theoretical Foundations, Suitability, and Algorithmic Analysis:
----------------------------------------------------------------
1. Problem Model:
   We are given a fleet of assets requiring preventive maintenance. Each asset has
   a deadline (next_due_date). A maintenance team has a fixed daily capacity C
   (maximum assets that can be serviced per calendar day). Service cannot occur prior
   to the asset's earliest permissible date (which is max(today, due_date) for
   routine maintenance, or starting from 'today' for overdue assets).

2. Earliest Deadline First (EDF) Suitability:
   - Jackson's Rule (1955) proved that on a single processor with uniform task
     durations where all jobs are ready at time 0, sequencing by Earliest Due Date
     strictly minimizes Maximum Lateness (L_max).
   - In preventive maintenance, servicing assets with the earliest due dates first
     directly mitigates high-risk overdue intervals and minimizes maximum delay.

3. Algorithm Limitations & Assumptions:
   - Heuristic vs. Global Optimality: While EDF is optimal for minimizing maximum
     lateness under basic unconstrained single-machine conditions, minimizing
     Total Lateness (or Total Tardiness sum(T_j)) under non-zero release times or
     multi-slot batch boundaries is generally NP-hard. Thus, EDF serves as an
     efficient, high-quality polynomial-time heuristic rather than a universally
     optimal solver for every tardiness objective.
   - Uniform Service Duration: Assumes each standard maintenance check consumes
     1 unit of technician capacity.
   - Non-preemption: Once assigned to a technician slot, the service completes
     on that scheduled date.

4. Computational Complexity:
   - Filtering eligible assets: O(N)
   - Priority Queue initialization (min-heapify): O(M) where M <= N is the number
     of eligible assets.
   - Extracting and scheduling each asset: M * O(log M) extractions.
   - Slot date assignment: O(1) per asset using monotonic forward pointer arithmetic
     (avoiding calendar date iteration loops).
   - Total Time Complexity: O(N log N), capable of processing 100,000 assets in seconds.
   - Total Space Complexity: O(N) auxiliary memory.
"""

from collections import defaultdict
from datetime import date, timedelta
import heapq
from typing import Dict, Iterable, List, Optional
try:
    from .models import Asset, ScheduledService, ScheduleResult
except ImportError:
    from models import Asset, ScheduledService, ScheduleResult


class MaintenanceScheduler:
    """Capacity-constrained preventive maintenance scheduler utilizing a min-heap EDF queue."""

    def __init__(
        self,
        daily_capacity: int = 5,
        horizon_days: Optional[int] = 60,
    ) -> None:
        """Initialize scheduler with operational constraints.

        Args:
            daily_capacity: Maximum number of maintenance services per calendar day (must be > 0).
            horizon_days: Lookahead window from today (in days). Assets due beyond this horizon
                are deferred to future scheduling cycles. If None, schedules all assets.

        Raises:
            ValueError: If daily_capacity <= 0 or horizon_days < 0.
        """
        if daily_capacity <= 0:
            raise ValueError(f"Daily capacity must be a positive integer (> 0), got {daily_capacity}")
        if horizon_days is not None and horizon_days < 0:
            raise ValueError(f"Horizon days cannot be negative, got {horizon_days}")

        self.daily_capacity: int = daily_capacity
        self.horizon_days: Optional[int] = horizon_days

    def schedule(
        self,
        assets: Iterable[Asset],
        today: date,
    ) -> ScheduleResult:
        """Execute capacity-constrained EDF maintenance scheduling.

        Args:
            assets: Iterable of Asset objects to schedule.
            today: Reference current calendar date.

        Returns:
            ScheduleResult containing scheduled service details, daily breakdown,
            and aggregate lateness performance metrics.
        """
        # 1. Filter assets requiring service: overdue assets + assets within scheduling horizon
        horizon_cutoff: Optional[date] = None
        if self.horizon_days is not None:
            horizon_cutoff = today + timedelta(days=self.horizon_days)

        eligible_assets: List[Asset] = []
        overdue_count: int = 0

        for asset in assets:
            if asset.is_overdue(today):
                overdue_count += 1
                eligible_assets.append(asset)
            elif horizon_cutoff is None or asset.next_due_date <= horizon_cutoff:
                eligible_assets.append(asset)

        if not eligible_assets:
            return ScheduleResult(
                services=[],
                daily_schedule={},
                total_lateness=0,
                max_lateness=0,
                overdue_count=0,
                total_scheduled=0,
                daily_capacity=self.daily_capacity,
                horizon_days=self.horizon_days,
            )

        # 2. Build Min-Heap for Earliest Deadline First (EDF)
        # Heap elements: (next_due_date, asset_id, asset)
        # Deterministic tie-breaking is enforced by asset_id
        heap: List[tuple] = [
            (asset.next_due_date, asset.asset_id, asset)
            for asset in eligible_assets
        ]
        heapq.heapify(heap)

        # 3. Schedule slots with capacity constraints
        # Monotonic pointer tracking guarantees O(1) scheduling step per job:
        # Since jobs are extracted in ascending order of due_date, the target earliest date
        # max(today, due_date) is monotonically non-decreasing.
        current_slot_date: date = today
        current_slot_usage: int = 0

        scheduled_services: List[ScheduledService] = []
        daily_schedule: Dict[date, List[ScheduledService]] = defaultdict(list)
        total_lateness: int = 0
        max_lateness: int = 0

        while heap:
            _, _, asset = heapq.heappop(heap)

            # Earliest possible service date: cannot service in the past
            target_date: date = max(today, asset.next_due_date)

            # If the current slot date lags behind target_date, advance directly
            if target_date > current_slot_date:
                current_slot_date = target_date
                current_slot_usage = 0

            # Assign service to current_slot_date
            service = ScheduledService(
                asset=asset,
                scheduled_date=current_slot_date,
                due_date=asset.next_due_date,
            )
            scheduled_services.append(service)
            daily_schedule[current_slot_date].append(service)

            # Update metrics
            lateness = service.lateness
            total_lateness += lateness
            if lateness > max_lateness:
                max_lateness = lateness

            # Increment daily capacity usage
            current_slot_usage += 1
            if current_slot_usage >= self.daily_capacity:
                current_slot_date += timedelta(days=1)
                current_slot_usage = 0

        return ScheduleResult(
            services=scheduled_services,
            daily_schedule=dict(daily_schedule),
            total_lateness=total_lateness,
            max_lateness=max_lateness,
            overdue_count=overdue_count,
            total_scheduled=len(scheduled_services),
            daily_capacity=self.daily_capacity,
            horizon_days=self.horizon_days,
        )

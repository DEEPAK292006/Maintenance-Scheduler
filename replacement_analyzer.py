"""
Replacement candidate detection and urgency analysis.

Assumptions and Limitations:
- The input dataset records historical repair counts and the last service date,
  but does not provide total asset operating lifetime or machine age.
- As a practical proxy, the period between last service date and today is used
  as an explicitly labeled approximation of the observation window.
- A minimum observation window (e.g., 30 days) is enforced to prevent division
  by zero and avoid volatile or hyper-inflated failure rate figures for recently
  serviced equipment.
- WARNING / DISCLAIMER: This failure-rate metric serves as a heuristic operational
  proxy for maintenance triaging, NOT a statistically rigorous reliability or
  Weibull life-data prediction.
"""

from datetime import date
from typing import Iterable, List
try:
    from .models import Asset, ReplacementCandidate
except ImportError:
    from models import Asset, ReplacementCandidate


class ReplacementAnalyzer:
    """Analyzes assets for replacement suitability and calculates prioritized urgency rankings."""

    @staticmethod
    def analyze(
        assets: Iterable[Asset],
        today: date,
        threshold: int = 3,
        min_observation_days: int = 30,
    ) -> List[ReplacementCandidate]:
        """Detect and rank all replacement candidates according to calculated urgency.

        Replacement Eligibility:
            Determined strictly by repair count: assets with historical repairs >= threshold
            (default 3) qualify as replacement candidates.

        Urgency Ranking Rule:
            Candidates are prioritized by a composite Urgency Score:
            urgency_score = failure_rate * (1.5 if is_overdue else 1.0) + (days_overdue / 30.0)

            Sorting order:
            1. Highest urgency_score first (descending)
            2. Earliest next_due_date (ascending)
            3. asset_id (ascending deterministic tie-breaker)

        Args:
            assets: Iterable of Asset objects to analyze.
            today: Reference current date.
            threshold: Minimum repairs required for candidate status (default 3).
            min_observation_days: Minimum days to clamp observation window (default 30).

        Returns:
            List of ReplacementCandidate objects sorted from most urgent to least urgent.
        """
        candidates: List[ReplacementCandidate] = []

        for asset in assets:
            if asset.is_replacement_candidate(threshold):
                rate = asset.estimate_failure_rate(today, min_observation_days)
                overdue = asset.is_overdue(today)
                overdue_days = asset.days_overdue(today)
                score = asset.replacement_urgency_score(today, min_observation_days)

                candidates.append(
                    ReplacementCandidate(
                        asset=asset,
                        repairs=asset.repairs,
                        failure_rate=rate,
                        is_overdue=overdue,
                        days_overdue=overdue_days,
                        urgency_score=score,
                    )
                )

        # Sort: urgency_score DESC, next_due_date ASC, asset_id ASC
        candidates.sort(
            key=lambda c: (-c.urgency_score, c.asset.next_due_date, c.asset.asset_id)
        )
        return candidates

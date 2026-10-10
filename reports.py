"""
Report generation and output formatting for maintenance scheduler results.

Keeps presentation logic completely decoupled from algorithmic computation.
"""

from datetime import date
from typing import List
try:
    from .models import Asset, ReplacementCandidate, ScheduleResult
except ImportError:
    from models import Asset, ReplacementCandidate, ScheduleResult


class ReportGenerator:
    """Formats system analysis into standardized terminal and structured reports."""

    @staticmethod
    def format_key_records(
        overdue_assets: List[Asset],
        replacement_candidates: List[ReplacementCandidate],
        today: date,
    ) -> str:
        """Format the mandatory primary output records according to project specifications.

        Expected format:
            OVERDUE <asset_id> <N> days
            REPLACE <asset_id>

        Args:
            overdue_assets: List of overdue assets sorted deterministically.
            replacement_candidates: List of replacement candidates sorted by urgency.
            today: Reference current date.

        Returns:
            Formatted string of key records.
        """
        lines: List[str] = []

        # Overdue records: OVERDUE <asset_id> <N> days
        for asset in overdue_assets:
            days = asset.days_overdue(today)
            lines.append(f"OVERDUE {asset.asset_id} {days} days")

        # Replacement records: REPLACE <asset_id>
        for cand in replacement_candidates:
            lines.append(f"REPLACE {cand.asset.asset_id}")

        return "\n".join(lines)

    @staticmethod
    def format_overdue_table(overdue_assets: List[Asset], today: date) -> str:
        """Generate a structured summary table of overdue assets."""
        if not overdue_assets:
            return "No assets are currently overdue for maintenance."

        header = f"{'ASSET ID':<12} | {'NEXT DUE':<12} | {'DAYS OVERDUE':<14} | {'INTERVAL':<10} | {'REPAIRS':<8}"
        separator = "-" * len(header)
        rows = [header, separator]

        for a in overdue_assets:
            rows.append(
                f"{a.asset_id:<12} | {str(a.next_due_date):<12} | "
                f"{a.days_overdue(today):<14} | {a.interval_days:<10} | {a.repairs:<8}"
            )
        return "\n".join(rows)

    @staticmethod
    def format_replacement_table(candidates: List[ReplacementCandidate]) -> str:
        """Generate an urgency-prioritized replacement evaluation report."""
        if not candidates:
            return "No assets currently meet the replacement criteria (historical repairs >= threshold)."

        header = (
            f"{'PRIORITY':<8} | {'ASSET ID':<10} | {'REPAIRS':<8} | "
            f"{'FAILURE RATE (rep/yr)':<22} | {'OVERDUE?':<10} | {'URGENCY SCORE':<14}"
        )
        separator = "-" * len(header)
        rows = [header, separator]

        for idx, c in enumerate(candidates, start=1):
            overdue_str = f"Yes ({c.days_overdue}d)" if c.is_overdue else "No"
            rows.append(
                f"{idx:<8} | {c.asset.asset_id:<10} | {c.repairs:<8} | "
                f"{c.failure_rate:<22.2f} | {overdue_str:<10} | {c.urgency_score:<14.2f}"
            )
        return "\n".join(rows)

    @staticmethod
    def format_upcoming_table(upcoming_assets: List[Asset], today: date) -> str:
        """Generate a report for assets due within 30 days (Feature F)."""
        if not upcoming_assets:
            return "No assets are due for maintenance in the next 30 days."

        header = (
            f"{'ASSET ID':<12} | {'NEXT DUE DATE':<14} | {'DAYS REMAINING':<16} | "
            f"{'REPAIRS':<10} | {'REPLACE CANDIDATE?':<18}"
        )
        separator = "-" * len(header)
        rows = [header, separator]

        for a in upcoming_assets:
            replace_status = "YES (REPLACE)" if a.is_replacement_candidate() else "No"
            rows.append(
                f"{a.asset_id:<12} | {str(a.next_due_date):<14} | "
                f"{a.days_remaining(today):<16} | {a.repairs:<10} | {replace_status:<18}"
            )
        return "\n".join(rows)

    @staticmethod
    def format_schedule_summary(result: ScheduleResult) -> str:
        """Generate a detailed report of the capacity-constrained technician schedule."""
        lines: List[str] = [
            "=" * 60,
            "TECHNICIAN CAPACITY & EDF SCHEDULE SUMMARY",
            "=" * 60,
            f"Daily Technician Capacity : {result.daily_capacity} assets/day",
            f"Scheduling Horizon        : {result.horizon_days if result.horizon_days is not None else 'Unbounded'} days",
            f"Overdue Assets Identified : {result.overdue_count}",
            f"Total Services Scheduled  : {result.total_scheduled}",
            f"Total Schedule Lateness   : {result.total_lateness} day(s)",
            f"Maximum Asset Lateness    : {result.max_lateness} day(s)",
            "-" * 60,
            "DAILY SERVICE ROSTER:",
        ]

        if not result.daily_schedule:
            lines.append("  (No services scheduled within current parameters)")
            return "\n".join(lines)

        sorted_days = sorted(result.daily_schedule.keys())
        for day in sorted_days:
            services = result.daily_schedule[day]
            lines.append(f"\nDate: {day} (Total Services: {len(services)}/{result.daily_capacity})")
            for svc in services:
                late_txt = f"[LATE by {svc.lateness} days]" if svc.lateness > 0 else "[ON TIME]"
                lines.append(
                    f"  - Asset {svc.asset.asset_id:<8} (Due: {svc.due_date}) {late_txt}"
                )

        return "\n".join(lines)

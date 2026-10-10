"""
Main entry point for the Maintenance Scheduler CLI application.

Coordinates input loading, overdue detection, replacement triaging,
capacity-constrained EDF scheduling, and report generation.
"""

import argparse
from datetime import date
from pathlib import Path
import sys
from typing import List, Optional

# Ensure project modules are resolvable
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from asset_manager import AssetManager
from config import (
    DEFAULT_DAILY_CAPACITY,
    DEFAULT_HORIZON_DAYS,
    REPLACEMENT_REPAIR_THRESHOLD,
    UPCOMING_WINDOW_DAYS,
)
from input_handler import InputHandler, InputValidationError
from models import Asset, ReplacementCandidate, ScheduleResult
from replacement_analyzer import ReplacementAnalyzer
from reports import ReportGenerator
from scheduler import MaintenanceScheduler


def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse CLI options and flags."""
    parser = argparse.ArgumentParser(
        description=(
            "Maintenance Scheduler: Capacity-Constrained Preventive Maintenance "
            "and Asset Replacement Prioritization."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        default=None,
        help="Path to input text file. If omitted or '-', reads from standard input (stdin).",
    )
    parser.add_argument(
        "-c",
        "--capacity",
        type=int,
        default=DEFAULT_DAILY_CAPACITY,
        help="Daily technician maintenance capacity (max assets serviced per day).",
    )
    parser.add_argument(
        "-H",
        "--horizon",
        type=int,
        default=DEFAULT_HORIZON_DAYS,
        help="Preventive scheduling horizon lookahead in days (use --all to unbind).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Schedule all assets without horizon restriction.",
    )
    parser.add_argument(
        "-t",
        "--threshold",
        type=int,
        default=REPLACEMENT_REPAIR_THRESHOLD,
        help="Historical repair count threshold to flag asset for replacement.",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Display comprehensive analytical tables in addition to primary key outputs.",
    )
    return parser.parse_args(args)


def run_scheduler_pipeline(
    today: date,
    assets: List[Asset],
    daily_capacity: int,
    horizon_days: Optional[int],
    replacement_threshold: int,
    detailed: bool = False,
) -> int:
    """Execute the core maintenance scheduling and reporting pipeline."""
    # 1. Overdue Maintenance Analysis (Feature C)
    overdue_assets = AssetManager.get_overdue_assets(assets, today)

    # 2. Replacement Urgency Analysis (Feature D)
    replacement_candidates = ReplacementAnalyzer.analyze(
        assets,
        today=today,
        threshold=replacement_threshold,
    )

    # 3. Preventive Maintenance Due in 30 Days (Feature F)
    upcoming_assets = AssetManager.get_upcoming_assets(
        assets,
        today=today,
        window_days=UPCOMING_WINDOW_DAYS,
    )

    # 4. Capacity-Constrained EDF Scheduling (Feature E)
    scheduler = MaintenanceScheduler(
        daily_capacity=daily_capacity,
        horizon_days=horizon_days,
    )
    schedule_result = scheduler.schedule(assets, today=today)

    # 5. Output Reporting
    # Primary Key Records (strictly required format)
    key_output = ReportGenerator.format_key_records(
        overdue_assets=overdue_assets,
        replacement_candidates=replacement_candidates,
        today=today,
    )
    if key_output:
        print(key_output)
    else:
        print("No overdue assets or replacement candidates identified.")

    # Detailed Analytical Sections
    if detailed:
        print("\n" + "=" * 70)
        print("DETAILED MAINTENANCE ANALYSIS REPORTS")
        print("=" * 70)

        print("\n[SECTION 1: OVERDUE ASSETS]")
        print(ReportGenerator.format_overdue_table(overdue_assets, today))

        print("\n[SECTION 2: REPLACEMENT CANDIDATES PRIORITIZATION]")
        print(ReportGenerator.format_replacement_table(replacement_candidates))

        print("\n[SECTION 3: PREVENTIVE MAINTENANCE DUE IN NEXT 30 DAYS]")
        print(ReportGenerator.format_upcoming_table(upcoming_assets, today))

        print("\n[SECTION 4: CAPACITY-CONSTRAINED SCHEDULE & METRICS]")
        print(ReportGenerator.format_schedule_summary(schedule_result))

    return 0


def main(cli_args: Optional[List[str]] = None) -> int:
    """CLI application entry point."""
    args = parse_arguments(cli_args)

    # Validate CLI arguments
    if args.capacity <= 0:
        print(f"Error: Daily capacity must be a positive integer, got {args.capacity}.", file=sys.stderr)
        return 1
    if args.horizon < 0:
        print(f"Error: Horizon days cannot be negative, got {args.horizon}.", file=sys.stderr)
        return 1

    horizon = None if args.all else args.horizon

    # Ingest and validate data
    try:
        if args.input_file and args.input_file != "-":
            today, assets = InputHandler.read_from_file(args.input_file)
        else:
            today, assets = InputHandler.read_from_stdin()
    except InputValidationError as err:
        print(f"Validation Error: {err}", file=sys.stderr)
        return 1
    except FileNotFoundError as err:
        print(f"File Error: {err}", file=sys.stderr)
        return 1
    except Exception as err:
        print(f"Unexpected Error during input processing: {err}", file=sys.stderr)
        return 1

    return run_scheduler_pipeline(
        today=today,
        assets=assets,
        daily_capacity=args.capacity,
        horizon_days=horizon,
        replacement_threshold=args.threshold,
        detailed=args.detailed,
    )


if __name__ == "__main__":
    sys.exit(main())

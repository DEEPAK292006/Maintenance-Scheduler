"""
Input parsing and validation module for the Maintenance Scheduler system.

Handles standard input (stdin) or text data files, performing strict validation
with explicit, actionable error messages.
"""

from datetime import date
from io import TextIOBase
from pathlib import Path
import sys
from typing import Iterable, Iterator, List, Optional, Set, Tuple, Union
try:
    from .date_utils import parse_date
    from .models import Asset
except ImportError:
    from date_utils import parse_date
    from models import Asset


class InputValidationError(ValueError):
    """Custom exception raised when input fails structural or logical validation."""

    def __init__(self, line_num: Optional[int], message: str) -> None:
        self.line_num = line_num
        self.message = message
        loc = f"Line {line_num}: " if line_num is not None else ""
        super().__init__(f"{loc}{message}")


class InputHandler:
    """Parses and validates maintenance scheduling datasets."""

    @classmethod
    def read_from_file(cls, file_path: Union[str, Path]) -> Tuple[date, List[Asset]]:
        """Read and validate maintenance input from a text file path."""
        p = Path(file_path)
        if not p.is_file():
            raise FileNotFoundError(f"Input file not found at: {p.resolve()}")

        with open(p, "r", encoding="utf-8") as f:
            return cls.parse_stream(f)

    @classmethod
    def read_from_stdin(cls) -> Tuple[date, List[Asset]]:
        """Read and validate maintenance input from standard input."""
        return cls.parse_stream(sys.stdin)

    @classmethod
    def parse_lines(cls, lines: Iterable[str]) -> Tuple[date, List[Asset]]:
        """Parse an iterable of raw input lines (useful for testing and streaming)."""
        return cls.parse_stream(lines)

    @classmethod
    def parse_stream(cls, stream: Iterable[str]) -> Tuple[date, List[Asset]]:
        """Core parser validating dataset line by line.

        Format:
            Line 1: today's date in YYYY-MM-DD
            Line 2: number of assets, n (non-negative integer)
            Next n lines: <asset_id> <interval_days> <last_service_date> <repairs>

        Raises:
            InputValidationError: If any validation rule is violated.
        """
        line_num = 0

        def next_valid_line(it: Iterator[str]) -> Tuple[int, str]:
            nonlocal line_num
            for raw in it:
                line_num += 1
                stripped = raw.strip()
                if stripped:  # Skip blank lines between headers if any
                    return line_num, stripped
            return line_num, ""

        iterator = iter(stream)

        # 1. Parse Line 1: today's date
        ln, line1 = next_valid_line(iterator)
        if not line1:
            raise InputValidationError(None, "Input is empty; expected today's date on line 1.")
        try:
            today = parse_date(line1)
        except ValueError as err:
            raise InputValidationError(ln, f"Invalid date for 'today': {err}") from err

        # 2. Parse Line 2: number of assets n
        ln, line2 = next_valid_line(iterator)
        if not line2:
            raise InputValidationError(None, "Expected number of assets (n) on line 2, but reached EOF.")
        try:
            expected_n = int(line2)
            if expected_n < 0:
                raise ValueError("Asset count cannot be negative.")
        except ValueError as err:
            raise InputValidationError(ln, f"Invalid asset count 'n': {line2}. Must be non-negative integer.") from err

        # 3. Parse next n asset records
        assets: List[Asset] = []
        seen_ids: Set[str] = set()

        for record_idx in range(expected_n):
            ln, record_line = next_valid_line(iterator)
            if not record_line:
                raise InputValidationError(
                    None,
                    f"Premature EOF: Expected {expected_n} asset records, but only found {len(assets)}.",
                )

            tokens = record_line.split()
            if len(tokens) != 4:
                raise InputValidationError(
                    ln,
                    f"Malformed record. Expected 4 fields '<asset_id> <interval_days> <last_service_date> <repairs>', "
                    f"found {len(tokens)} tokens in '{record_line}'.",
                )

            asset_id, interval_str, last_date_str, repairs_str = tokens

            # Asset ID uniqueness
            if asset_id in seen_ids:
                raise InputValidationError(ln, f"Duplicate asset ID '{asset_id}' detected.")
            seen_ids.add(asset_id)

            # Service interval validation
            try:
                interval_days = int(interval_str)
                if interval_days <= 0:
                    raise ValueError("Service interval must be strictly positive (> 0).")
            except ValueError as err:
                raise InputValidationError(
                    ln,
                    f"Invalid service interval '{interval_str}' for asset '{asset_id}': {err}",
                ) from err

            # Last service date validation
            try:
                last_service_date = parse_date(last_date_str)
            except ValueError as err:
                raise InputValidationError(
                    ln,
                    f"Invalid last service date '{last_date_str}' for asset '{asset_id}': {err}",
                ) from err

            # Repairs validation
            try:
                repairs = int(repairs_str)
                if repairs < 0:
                    raise ValueError("Historical repairs count cannot be negative.")
            except ValueError as err:
                raise InputValidationError(
                    ln,
                    f"Invalid repair count '{repairs_str}' for asset '{asset_id}': {err}",
                ) from err

            asset = Asset(
                asset_id=asset_id,
                interval_days=interval_days,
                last_service_date=last_service_date,
                repairs=repairs,
            )
            assets.append(asset)

        return today, assets

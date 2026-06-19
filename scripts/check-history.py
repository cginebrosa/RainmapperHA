#!/usr/bin/env python3
"""Validate Rainmapper historical CSV files before and after risky changes.

The historical incrementals in Data/ are the most valuable project artifact.
This script performs lightweight structural checks that are safe to run often:
it verifies headers, duplicate columns and non-empty row counts, and optionally
compares a new Data directory with a previous backup/copy.
"""

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CsvSummary:
    path: Path
    columns: list[str]
    rows: int


def read_csv_summary(path: Path) -> CsvSummary:
    """Read one CSV and return the minimal metadata needed for safety checks."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        try:
            columns = next(reader)
        except StopIteration as exc:
            raise ValueError("CSV is empty") from exc

        if not columns or all(not column.strip() for column in columns):
            raise ValueError("CSV header is empty")

        normalized = [column.strip() for column in columns]
        duplicates = sorted({column for column in normalized if normalized.count(column) > 1})
        if duplicates:
            raise ValueError(f"CSV has duplicate columns: {', '.join(duplicates)}")

        # Count only meaningful data rows so trailing blank lines do not matter.
        rows = 0
        for row in reader:
            if row and any(cell.strip() for cell in row):
                rows += 1

    return CsvSummary(path=path, columns=normalized, rows=rows)


def find_csv_files(data_dir: Path) -> list[Path]:
    """Return CSV files from a candidate Rainmapper Data directory."""
    if not data_dir.exists():
        raise ValueError(f"Data directory does not exist: {data_dir}")
    if not data_dir.is_dir():
        raise ValueError(f"Data path is not a directory: {data_dir}")
    return sorted(data_dir.glob("*.csv"))


def load_summaries(data_dir: Path) -> dict[str, CsvSummary]:
    """Load summaries for all CSV files in a Data directory."""
    csv_files = find_csv_files(data_dir)
    if not csv_files:
        raise ValueError(f"No CSV files found in: {data_dir}")

    summaries = {}
    for path in csv_files:
        summaries[path.name] = read_csv_summary(path)
    return summaries


def compare_summaries(
    before: dict[str, CsvSummary],
    after: dict[str, CsvSummary],
    allow_row_drop: bool,
) -> list[str]:
    """Compare a baseline and a new Data directory for destructive changes."""
    errors = []

    for name, before_summary in before.items():
        after_summary = after.get(name)
        if after_summary is None:
            errors.append(f"{name}: missing after run")
            continue

        if before_summary.columns != after_summary.columns:
            errors.append(f"{name}: columns changed")

        if not allow_row_drop and after_summary.rows < before_summary.rows:
            errors.append(
                f"{name}: row count decreased from {before_summary.rows} to {after_summary.rows}"
            )

    return errors


def print_summaries(label: str, summaries: dict[str, CsvSummary]) -> None:
    """Print a compact human-readable summary for each CSV file."""
    print(label)
    for name, summary in summaries.items():
        print(f"  {name}: {summary.rows} row(s), {len(summary.columns)} column(s)")


def parse_args() -> argparse.Namespace:
    """Parse CLI options for standalone shell usage and smoke tests."""
    parser = argparse.ArgumentParser(
        description="Validate Rainmapper historical CSV files before or after risky data changes."
    )
    parser.add_argument(
        "data_dir",
        type=Path,
        help="Data directory to validate, for example Data or docker-data/Data.",
    )
    parser.add_argument(
        "--compare-before",
        type=Path,
        help="Optional previous Data directory to compare against.",
    )
    parser.add_argument(
        "--allow-row-drop",
        action="store_true",
        help="Allow row counts to decrease when comparing before/after directories.",
    )
    return parser.parse_args()


def main() -> int:
    """Run validation and return a process exit code."""
    args = parse_args()

    try:
        after = load_summaries(args.data_dir)
        print_summaries(f"Validated {args.data_dir}", after)

        if args.compare_before:
            before = load_summaries(args.compare_before)
            print_summaries(f"Baseline {args.compare_before}", before)
            errors = compare_summaries(before, after, args.allow_row_drop)
            if errors:
                print("History comparison failed:", file=sys.stderr)
                for error in errors:
                    print(f"  - {error}", file=sys.stderr)
                return 1
    except ValueError as exc:
        print(f"History check failed: {exc}", file=sys.stderr)
        return 1

    print("History check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

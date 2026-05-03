#!/usr/bin/env python3
"""
run.py — Master runner for the API Automation Framework.

Usage:
    python run.py                        # full run, default settings
    python run.py --dry-run              # validate setup, skip HTTP
    python run.py --workers 16           # override thread count
    python run.py --batch 1000           # override batch size
    python run.py --input path/to/input.csv --expected path/to/exp.csv
    python run.py --template path/to/template.json

All flags are optional — defaults come from config/settings.py.
"""

import argparse
import json
import os
import sys
import time

# ── Make imports work from project root ──────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from settings import (
    INPUT_CSV, EXPECTED_CSV, REQUEST_TEMPLATE,
    BATCH_SIZE, MAX_WORKERS, SUMMARY_REPORT
)
from executor import run_all


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="API Automation Framework Runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input",    default=INPUT_CSV,       help="Input CSV path")
    parser.add_argument("--expected", default=EXPECTED_CSV,    help="Expected output CSV path")
    parser.add_argument("--template", default=REQUEST_TEMPLATE,help="Request template JSON path")
    parser.add_argument("--workers",  type=int, default=MAX_WORKERS, help="Parallel thread count")
    parser.add_argument("--batch",    type=int, default=BATCH_SIZE,  help="Batch size")
    parser.add_argument("--start-row",type=int, default=1,     help="Start from row number (1-indexed)")
    parser.add_argument("--limit",    type=int, default=None,  help="Test only N rows (None = all)")
    parser.add_argument("--dry-run",  action="store_true",     help="Skip HTTP, validate setup only")
    return parser.parse_args()


def preflight_checks(args: argparse.Namespace) -> bool:
    """Validate that all required files exist before starting."""
    ok = True
    for label, path in [
        ("Input CSV",    args.input),
        ("Expected CSV", args.expected),
        ("Template JSON",args.template),
    ]:
        if not os.path.exists(path):
            print(f"  ✗  {label} not found: {path}")
            ok = False
        else:
            size_mb = os.path.getsize(path) / 1_048_576
            print(f"  ✓  {label}: {path}  ({size_mb:.1f} MB)")
    return ok


def main() -> int:
    args = parse_args()

    print("\n" + "=" * 70)
    print("  API AUTOMATION FRAMEWORK")
    print("=" * 70)
    print("\nPre-flight checks:")
    if not preflight_checks(args):
        print("\n[ABORT] Fix missing files above and re-run.\n")
        return 1

    print(f"\nConfiguration:")
    print(f"  Workers : {args.workers}")
    print(f"  Batch   : {args.batch}")
    print(f"  Dry-run : {args.dry_run}")
    print()

    summary = run_all(
        input_csv    = args.input,
        expected_csv = args.expected,
        template_path= args.template,
        max_workers  = args.workers,
        batch_size   = args.batch,
        start_row    = args.start_row,
        limit        = args.limit,
        dry_run      = args.dry_run,
    )

    if args.dry_run:
        print("Dry run complete. No HTTP requests were made.")
        return 0

    # ── Print final summary table ─────────────────────────────────────────────
    total   = summary.get("total", 0)
    passed  = summary.get("passed", 0)
    failed  = summary.get("failed", 0)
    errors  = summary.get("errors", 0)
    elapsed = summary.get("elapsed_sec", 0)
    tput    = summary.get("throughput_per_sec", 0)
    pass_pct = (passed / total * 100) if total else 0

    print("\n" + "=" * 70)
    print(f"  RESULTS SUMMARY")
    print("=" * 70)
    print(f"  Total cases   : {total:>10,}")
    print(f"  PASS          : {passed:>10,}  ({pass_pct:.1f}%)")
    print(f"  FAIL          : {failed:>10,}")
    print(f"  ERRORS        : {errors:>10,}")
    print(f"  Elapsed       : {elapsed:>10.1f}s")
    print(f"  Throughput    : {tput:>10} tests/sec")
    print(f"\n  Full report   : {SUMMARY_REPORT}")
    print("=" * 70 + "\n")

    # Non-zero exit if any failures/errors — useful in CI pipelines
    return 0 if (failed == 0 and errors == 0) else 1


if __name__ == "__main__":
    sys.exit(main())

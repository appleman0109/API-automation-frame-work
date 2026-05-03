"""
Test executor.
Ties together: CSV read → payload build → HTTP send → validate → report.
Supports both single-threaded (safe, debuggable) and multi-threaded (fast) modes.

Only built-ins: concurrent.futures, threading.
"""

from __future__ import annotations

import concurrent.futures
import time
from typing import Dict, Any, Optional

from settings import (
    INPUT_CSV, EXPECTED_CSV, REQUEST_TEMPLATE,
    BATCH_SIZE, MAX_WORKERS
)
from csv_reader    import iter_batches, zip_input_expected, count_rows
from payload_builder import load_template, build_payload, get_placeholders
from http_client   import send_request
from validator     import validate, ValidationResult
from reporter      import ReportWriter, ProgressCounter
from response_logger import ResponseLogger
from logger        import log_pass, log_fail, log_error, log_info


def _run_single_test(
    test_id:      str,
    input_row:    Dict[str, str],
    expected_row: Dict[str, str],
    template:     Dict[str, Any],
) -> ValidationResult:
    """
    Execute one test case end-to-end.
    This function is the unit of parallelism — each worker calls this.
    """
    try:
        import json
        test_case_name = input_row.get('test_case_name', '')
        payload      = build_payload(template, input_row)
        status, resp = send_request(payload)
        request_dict = json.loads(payload.decode('utf-8'))
        result       = validate(test_id, resp, expected_row, status, test_case_name, request_dict)
        return result

    except Exception as exc:
        # Return a result that marks the test as errored, not failed
        return ValidationResult(
            test_id=test_id,
            passed=False,
            http_status=0,
            error=str(exc),
        )


def _flush_logs(result: ValidationResult) -> None:
    """Write pass/fail/error log lines for a completed result."""
    if result.error:
        log_error(result.test_id, result.error)
    elif result.passed:
        log_pass(result.test_id)
    else:
        failed_details = ", ".join([
            f"{fr.field_path}: expected {fr.expected}, got {fr.actual}"
            for fr in result.field_results if not fr.passed
        ])
        log_fail(result.test_id, failed_details)


def run_all(
    input_csv:   str = INPUT_CSV,
    expected_csv: str = EXPECTED_CSV,
    template_path: str = REQUEST_TEMPLATE,
    max_workers: int = MAX_WORKERS,
    batch_size:  int = BATCH_SIZE,
    start_row:   int = 1,
    limit:       int = None,
    dry_run:     bool = False,
) -> dict:
    """
    Main entry point.

    dry_run=True  → validate CSV/template compatibility, skip actual HTTP calls.
    Returns a summary dict with pass/fail/error counts.
    """
    start = time.time()
    log_info("=" * 70)
    log_info("API Automation Framework — starting run")
    log_info(f"  input_csv    : {input_csv}")
    log_info(f"  expected_csv : {expected_csv}")
    log_info(f"  template     : {template_path}")
    log_info(f"  max_workers  : {max_workers}")
    log_info(f"  batch_size   : {batch_size}")
    log_info(f"  start_row    : {start_row}")
    log_info(f"  limit        : {limit if limit else 'all'}")
    log_info(f"  dry_run      : {dry_run}")

    # ── Load template (once, shared across all threads) ──────────────────────
    template = load_template(template_path)
    placeholders = get_placeholders(template)
    log_info(f"  template placeholders: {len(placeholders)}")

    # ── Count rows for progress display (cheap linear scan) ──────────────────
    log_info("Counting test cases (fast scan)...")
    total = count_rows(input_csv)
    log_info(f"  Total test cases: {total:,}")

    if dry_run:
        log_info("DRY RUN — HTTP calls skipped. Exiting.")
        return {"total": total, "dry_run": True}

    progress = ProgressCounter(total=total, interval=1000)

    with ReportWriter() as reporter:
        with ResponseLogger() as reslog:
            # ── Process in batches to control memory ────────────────────────────
            for batch_num, (inp_batch, exp_batch) in enumerate(
                _zip_batches(input_csv, expected_csv, batch_size, start_row, limit), start=1
            ):
                futures_map = {}

                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
                    for inp_row, exp_row in zip(inp_batch, exp_batch):
                        test_id = inp_row.get("test_id", f"batch{batch_num}_row{len(futures_map)+1}")
                        future  = pool.submit(
                            _run_single_test,
                            test_id, inp_row, exp_row, template
                        )
                        futures_map[future] = test_id

                    for future in concurrent.futures.as_completed(futures_map):
                        result = future.result()
                        _flush_logs(result)
                        reporter.write(result)
                        if result.api_response:
                            reslog.write(result.test_id, result.test_case_name, result.api_request, result.api_response, result.http_status)
                        progress.update(passed=result.passed, error=bool(result.error))

    print()   # newline after progress bar
    elapsed = time.time() - start
    summary = progress.final_summary()
    summary["elapsed_sec"] = round(elapsed, 2)
    summary["throughput_per_sec"] = round(total / elapsed, 1) if elapsed > 0 else 0

    log_info("=" * 70)
    log_info(f"Run complete in {elapsed:.1f}s")
    log_info(f"  PASS   : {summary['passed']:,}")
    log_info(f"  FAIL   : {summary['failed']:,}")
    log_info(f"  ERRORS : {summary['errors']:,}")
    log_info(f"  Throughput: ~{summary['throughput_per_sec']} tests/sec")
    log_info("=" * 70)
    return summary


def _zip_batches(input_csv, expected_csv, batch_size, start_row=1, limit=None):
    """
    Zip the two CSVs into paired batches without loading either into memory.
    Yields (input_batch, expected_batch) tuples.
    
    Args:
        start_row: Row number to start from (1-indexed)
        limit: Maximum number of rows to process (None = all)
    """
    inp_gen = iter_batches(input_csv,    batch_size, start_row, limit)
    exp_gen = iter_batches(expected_csv, batch_size, start_row, limit)
    for inp_batch, exp_batch in zip(inp_gen, exp_gen):
        yield inp_batch, exp_batch

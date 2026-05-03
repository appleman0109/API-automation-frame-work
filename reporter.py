"""
Report writer.
Writes test results to a summary CSV incrementally (streaming).
Thread-safe via a lock — multiple workers can call write() concurrently.
Never buffers more than one row in memory.
Only built-ins: csv, threading, os.
"""

import csv
import threading
import os
from typing import Optional

from settings import SUMMARY_REPORT, REPORT_DIR
from validator import ValidationResult

_HEADERS = [
    "test_id", "test_case_name", "status", "http_status",
    "total_checked", "total_passed", "total_failed",
    "failed_fields", "error"
]


class ReportWriter:
    """
    Context-manager that opens the summary CSV once and appends rows
    as results come in from worker threads.

    Usage:
        with ReportWriter() as rw:
            rw.write(validation_result)
    """

    def __init__(self, filepath: str = SUMMARY_REPORT) -> None:
        os.makedirs(REPORT_DIR, exist_ok=True)
        self._filepath = filepath
        self._lock     = threading.Lock()
        self._fh       = None
        self._writer   = None

    def __enter__(self) -> "ReportWriter":
        self._fh     = open(self._filepath, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._fh, fieldnames=_HEADERS)
        self._writer.writeheader()
        self._fh.flush()
        return self

    def __exit__(self, *_) -> None:
        if self._fh:
            self._fh.flush()
            self._fh.close()

    def write(self, result: ValidationResult) -> None:
        """Append one result row. Safe to call from multiple threads."""
        failed_fields = "; ".join(
            f"{r.field_path}(exp={r.expected!r},got={r.actual!r})"
            for r in result.failures
        )
        row = {
            "test_id":       result.test_id,
            "test_case_name": result.test_case_name,
            "status":        "PASS" if result.passed else "FAIL",
            "http_status":   result.http_status,
            "total_checked": result.total_checked,
            "total_passed":  result.total_passed,
            "total_failed":  len(result.failures),
            "failed_fields": failed_fields,
            "error":         result.error or "",
        }
        with self._lock:
            self._writer.writerow(row)
            # Flush every row so partial results survive a crash
            self._fh.flush()


class ProgressCounter:
    """
    Lock-free-ish progress counter using threading primitives.
    Prints a progress line to stdout every `interval` completions.
    """

    def __init__(self, total: int, interval: int = 1000) -> None:
        self._total    = total
        self._interval = interval
        self._done     = 0
        self._passed   = 0
        self._failed   = 0
        self._errors   = 0
        self._lock     = threading.Lock()

    def update(self, passed: bool, error: bool = False) -> None:
        with self._lock:
            self._done += 1
            if error:
                self._errors += 1
            elif passed:
                self._passed += 1
            else:
                self._failed += 1
            if self._done % self._interval == 0 or self._done == self._total:
                pct = self._done / self._total * 100
                print(
                    f"\r  Progress: {self._done:>7,}/{self._total:,} ({pct:5.1f}%) "
                    f"| PASS={self._passed:,} FAIL={self._failed:,} ERR={self._errors:,}",
                    end="", flush=True
                )

    def final_summary(self) -> dict:
        return {
            "total":   self._total,
            "done":    self._done,
            "passed":  self._passed,
            "failed":  self._failed,
            "errors":  self._errors,
        }

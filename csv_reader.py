"""
Memory-efficient CSV reader.
Streams rows one at a time — never loads the full 5-lakh row file into RAM.
Supports both plain CSV and auto-detected dialect.
Only built-ins: csv, io, os.
"""

import csv
import os
from typing import Iterator, Dict, List, Tuple, Optional


def iter_csv_rows(filepath: str) -> Iterator[Dict[str, str]]:
    """
    Yield one row at a time as {column: value} dicts.
    Memory footprint = O(1 row), not O(N rows).
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CSV not found: {filepath}")

    with open(filepath, newline="", encoding="utf-8-sig") as fh:
        # Sniff dialect from first 4 KB so we handle semicolon-separated exports too
        sample = fh.read(4096)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel        # safe default

        reader = csv.DictReader(fh, dialect=dialect)
        for row in reader:
            # Strip whitespace from keys & values (Excel exports often pad)
            yield {k.strip(): v.strip() for k, v in row.items()}


def iter_batches(filepath: str, batch_size: int, start_row: int = 1, limit: int = None) -> Iterator[List[Dict[str, str]]]:
    """
    Yield lists of `batch_size` rows.
    Useful when you want to fan-out to a thread pool per batch.
    
    Args:
        start_row: Row number to start from (1-indexed, default=1)
        limit: Maximum number of rows to process (None = all)
    """
    batch: List[Dict[str, str]] = []
    row_count = 0
    
    for i, row in enumerate(iter_csv_rows(filepath), start=1):
        # Skip rows before start_row
        if i < start_row:
            continue
        
        # Stop if we've reached the limit
        if limit and row_count >= limit:
            break
        
        batch.append(row)
        row_count += 1
        
        if len(batch) >= batch_size:
            yield batch
            batch = []
    
    if batch:
        yield batch           # final partial batch


def get_csv_headers(filepath: str) -> List[str]:
    """Return only the header row without reading the whole file."""
    with open(filepath, newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        return [h.strip() for h in next(reader)]


def zip_input_expected(
    input_csv: str,
    expected_csv: str
) -> Iterator[Tuple[Dict[str, str], Dict[str, str]]]:
    """
    Lazily pair input rows with expected rows by position.
    Both files must have the same number of rows.
    Avoids loading either file fully.
    """
    for inp, exp in zip(iter_csv_rows(input_csv), iter_csv_rows(expected_csv)):
        yield inp, exp


def count_rows(filepath: str) -> int:
    """
    Count data rows without loading content.
    Used for progress display only — O(N) reads but O(1) memory.
    """
    count = 0
    with open(filepath, encoding="utf-8-sig") as fh:
        for _ in fh:
            count += 1
    return max(0, count - 1)   # subtract header row

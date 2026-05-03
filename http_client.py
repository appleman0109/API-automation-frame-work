"""
HTTP client wrapper.
Uses only http.client (stdlib) — no requests, no urllib3.
Supports HTTPS, connection reuse per-thread, and retry with exponential backoff.
"""

import http.client
import json
import time
import threading
from typing import Dict, Any, Optional, Tuple

from settings import (
    API_HOST, API_PORT, API_PATH, API_USE_HTTPS,
    API_TIMEOUT, API_HEADERS, RETRY_COUNT, RETRY_BACKOFF_SEC
)
from logger import log_debug, log_error

# ── Per-thread connection pool (one persistent connection per worker thread) ──
_local = threading.local()

# HTTP status codes that warrant a retry
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _get_connection() -> http.client.HTTPConnection:
    """
    Return a persistent connection for the current thread.
    Creates a new one if it doesn't exist or has been closed.
    """
    conn = getattr(_local, "conn", None)
    if conn is None:
        if API_USE_HTTPS:
            conn = http.client.HTTPSConnection(API_HOST, API_PORT, timeout=API_TIMEOUT)
        else:
            conn = http.client.HTTPConnection(API_HOST, API_PORT, timeout=API_TIMEOUT)
        _local.conn = conn
        log_debug(f"New connection created for thread {threading.current_thread().name}")
    return conn


def _close_connection() -> None:
    conn = getattr(_local, "conn", None)
    if conn:
        try:
            conn.close()
        except Exception:
            pass
        _local.conn = None


def send_request(payload_bytes: bytes) -> Tuple[int, Dict[str, Any]]:
    """
    POST `payload_bytes` to the configured endpoint.
    Returns (http_status_code, parsed_response_dict).

    Retries on transient errors up to RETRY_COUNT times.
    Raises RuntimeError if all retries are exhausted.
    """
    headers = {**API_HEADERS, "Content-Length": str(len(payload_bytes))}
    last_exc: Optional[Exception] = None

    for attempt in range(1, RETRY_COUNT + 2):   # +1 for the first attempt
        try:
            conn = _get_connection()
            conn.request("POST", API_PATH, body=payload_bytes, headers=headers)
            resp = conn.getresponse()
            status = resp.status
            body   = resp.read()

            if status in _RETRYABLE_STATUS and attempt <= RETRY_COUNT:
                wait = RETRY_BACKOFF_SEC * (2 ** (attempt - 1))
                log_debug(f"HTTP {status} — retry {attempt}/{RETRY_COUNT} in {wait}s")
                _close_connection()
                time.sleep(wait)
                continue

            try:
                data = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise RuntimeError(f"Non-JSON response (HTTP {status}): {body[:200]}") from exc

            return status, data

        except (http.client.HTTPException, OSError, ConnectionResetError) as exc:
            last_exc = exc
            _close_connection()
            if attempt <= RETRY_COUNT:
                wait = RETRY_BACKOFF_SEC * (2 ** (attempt - 1))
                log_debug(f"Connection error ({exc}) — retry {attempt}/{RETRY_COUNT} in {wait}s")
                time.sleep(wait)
            else:
                break

    raise RuntimeError(f"All {RETRY_COUNT} retries exhausted. Last error: {last_exc}")

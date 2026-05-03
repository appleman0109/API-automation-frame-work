"""
Response logger.
Stores complete API request and response JSON for each test case.
Thread-safe via lock — multiple workers can write concurrently.
Creates a JSONL file (one JSON per line) for easy analysis.
"""

import json
import threading
import os
from typing import Any, Dict

_RESPONSE_FILE = os.path.join(
    os.path.dirname(__file__), "reports", "api_responses.jsonl"
)


class ResponseLogger:
    """
    Context-manager that opens a JSONL file and logs API requests and responses.
    One JSON object per line, easy to parse with tools.
    
    Usage:
        with ResponseLogger() as rl:
            rl.write(test_id, test_case_name, request_payload, response_json, http_status)
    """

    def __init__(self, filepath: str = _RESPONSE_FILE):
        self._filepath = filepath
        self._fh = None
        self._lock = threading.Lock()

    def __enter__(self) -> "ResponseLogger":
        # Create reports directory if needed
        os.makedirs(os.path.dirname(self._filepath), exist_ok=True)
        self._fh = open(self._filepath, "w", encoding="utf-8")
        return self

    def __exit__(self, *_) -> None:
        if self._fh:
            self._fh.flush()
            self._fh.close()

    def write(self, test_id: str, test_case_name: str, request_payload: Dict[str, Any], response: Dict[str, Any], http_status: int) -> None:
        """
        Log a complete API request and response as JSON.
        Safe to call from multiple threads.
        """
        record = {
            "test_id": test_id,
            "test_case_name": test_case_name,
            "http_status": http_status,
            "request": request_payload,
            "response": response,
        }
        with self._lock:
            self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._fh.flush()

"""
Simple logger module — provides basic logging functions.
"""

def log_info(msg: str) -> None:
    """Log info message."""
    print(f"[INFO] {msg}")

def log_debug(msg: str) -> None:
    """Log debug message."""
    print(f"[DEBUG] {msg}")

def log_pass(test_id: str) -> None:
    """Log passing test."""
    print(f"[PASS] {test_id}")

def log_fail(test_id: str, reason: str = "") -> None:
    """Log failing test."""
    msg = f"[FAIL] {test_id}"
    if reason:
        msg += f" — {reason}"
    print(msg)

def log_error(test_id: str, error: str) -> None:
    """Log error."""
    print(f"[ERROR] {test_id} — {error}")

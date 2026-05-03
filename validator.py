"""
Response validator.
Compares the API response dict against the expected values from the CSV row.
Supports nested key access via dot notation: "order.status.code"
Returns a structured result object — no I/O, purely functional.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from settings import EXPECTED_COL_PREFIX, IGNORED_RESPONSE_FIELDS, STRICT_VALIDATION


@dataclass
class FieldResult:
    field_path:  str
    expected:    Any
    actual:      Any
    passed:      bool
    note:        str = ""


@dataclass
class ValidationResult:
    test_id:        str
    test_case_name: str = ""
    passed:         bool = False
    http_status:    int = 0
    field_results:  List[FieldResult] = field(default_factory=list)
    error:          Optional[str] = None
    api_response:   Optional[Dict[str, Any]] = None
    api_request:    Optional[Dict[str, Any]] = None

    @property
    def failures(self) -> List[FieldResult]:
        return [r for r in self.field_results if not r.passed]

    @property
    def total_checked(self) -> int:
        return len(self.field_results)

    @property
    def total_passed(self) -> int:
        return sum(1 for r in self.field_results if r.passed)


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _get_nested(obj: Any, path: str) -> Any:
    """
    Resolve a dot-notation path in a nested dict/list.
    e.g. "order.items.0.price"  →  obj["order"]["items"][0]["price"]
    Returns a sentinel if the path doesn't exist.
    """
    _MISSING = object()
    parts = path.split(".")
    cursor = obj
    for part in parts:
        if cursor is _MISSING:
            break
        if isinstance(cursor, dict):
            cursor = cursor.get(part, _MISSING)
        elif isinstance(cursor, list):
            try:
                cursor = cursor[int(part)]
            except (ValueError, IndexError):
                cursor = _MISSING
        else:
            cursor = _MISSING
    return None if cursor is _MISSING else cursor


def _coerce_expected(raw: str, actual: Any) -> Any:
    """
    Cast the CSV string to the same Python type as the actual value
    so "200" == 200 comparisons work correctly.
    """
    if raw == "" or raw is None:
        return None
    if isinstance(actual, bool):
        return raw.lower() in ("true", "1", "yes")
    if isinstance(actual, int):
        try:
            return int(raw)
        except ValueError:
            pass
    if isinstance(actual, float):
        try:
            return float(raw)
        except ValueError:
            pass
    return raw   # keep as string


# ─── Public API ───────────────────────────────────────────────────────────────

def validate(
    test_id:       str,
    response:      Dict[str, Any],
    expected_row:  Dict[str, str],
    http_status:   int,
    test_case_name: str = "",
    request:       Dict[str, Any] = None,
) -> ValidationResult:
    """
    Compare `response` against fields in `expected_row`.

    Convention:  expected_row columns prefixed with EXPECTED_COL_PREFIX
    are treated as expected-value assertions.
    The prefix is stripped to derive the response field path.

    Example:
        expected_row = {"exp_order.status": "SUCCESS", "exp_total": "150"}
        → checks response["order"]["status"] == "SUCCESS"
                   response["total"] == 150
    """
    field_results: List[FieldResult] = []
    overall_pass  = True

    for col, raw_expected in expected_row.items():
        if not col.startswith(EXPECTED_COL_PREFIX):
            continue

        field_path = col[len(EXPECTED_COL_PREFIX):]   # strip prefix

        if field_path in IGNORED_RESPONSE_FIELDS:
            continue

        actual    = _get_nested(response, field_path)
        expected  = _coerce_expected(raw_expected, actual)

        # If expected is blank, validate that actual is also blank/null/empty
        if raw_expected == "":
            is_blank = actual is None or actual == "" or (isinstance(actual, (list, dict)) and len(actual) == 0)
            passed = is_blank
            note = "blank expected" if passed else f"expected blank but got: {actual}"
            field_results.append(FieldResult(
                field_path=field_path, expected="<blank>", actual=actual,
                passed=passed, note=note
            ))
            if not passed and STRICT_VALIDATION:
                overall_pass = False
            continue

        passed = (actual == expected)
        note   = "" if passed else f"type(actual)={type(actual).__name__}"

        if not passed and STRICT_VALIDATION:
            overall_pass = False

        field_results.append(FieldResult(
            field_path=field_path,
            expected=expected,
            actual=actual,
            passed=passed,
            note=note,
        ))

    return ValidationResult(
        test_id=test_id,
        test_case_name=test_case_name,
        passed=overall_pass and all(r.passed for r in field_results),
        http_status=http_status,
        field_results=field_results,
        api_response=response,
        api_request=request,
    )

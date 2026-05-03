"""
Payload builder.
Loads the JSON request template ONCE, then fills dynamic placeholders
from each input CSV row at runtime.

Placeholder syntax in template:  "{{field_name}}"
Array replication: If a list contains objects with placeholders, and a CSV column
named "{{field_name}}_count" exists, that array item will be replicated N times.

Example:
  Template: { "items": [{"sku": "{{item_sku}}", "qty": "{{item_qty}}"}] }
  CSV: item_sku=SKU001, item_qty=2, items_count=3
  Result: items array with 3 identical objects filled with SKU001, 2

Only built-ins: json, re, copy.
"""

import json
import re
import copy
import os
from typing import Dict, Any

# Matches  {{some_field_name}}  anywhere in a JSON string value
_PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")


def load_template(filepath: str) -> Dict[str, Any]:
    """
    Read and parse the JSON template once.
    Returns the parsed dict — callers deepcopy before filling.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Template not found: {filepath}")
    with open(filepath, encoding="utf-8") as fh:
        return json.load(fh)


def _fill_value(value: Any, row: Dict[str, str], parent_key: str = "") -> Any:
    """
    Recursively walk a JSON value and substitute placeholders.
    Handles strings, dicts, lists, and scalars.
    Type-coercion: if the entire string is one placeholder, the
    replacement inherits its CSV type (int/float if parseable).
    
    Special handling for arrays:
    - If CSV has a "<array_name>_count" column, replicate array items that many times.
    """
    if isinstance(value, str):
        # Full-field replacement → try type coercion
        full_match = _PLACEHOLDER_RE.fullmatch(value)
        if full_match:
            key = full_match.group(1)
            raw = row.get(key, "")
            return _coerce(raw)

        # Partial replacement → keep as string, substitute in-place
        def replacer(m: re.Match) -> str:
            return row.get(m.group(1), "")

        return _PLACEHOLDER_RE.sub(replacer, value)

    elif isinstance(value, dict):
        return {k: _fill_value(v, row, k) for k, v in value.items()}

    elif isinstance(value, list):
        # Check if this array should be replicated
        replicate_count_key = f"{parent_key}_count"
        if replicate_count_key in row:
            try:
                count = int(row[replicate_count_key])
                # Fill the first item, then replicate it
                filled_items = [_fill_value(copy.deepcopy(item), row) for item in value]
                result = []
                for _ in range(count):
                    result.extend([copy.deepcopy(item) for item in filled_items])
                return result
            except (ValueError, IndexError):
                pass
        
        # Normal array processing (no replication)
        return [_fill_value(item, row) for item in value]

    # int, float, bool, None — return as-is
    return value


def _coerce(raw: str) -> Any:
    """Try to parse a string as int, then float, else keep as string."""
    if raw == "":
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    return raw


def build_payload(template: Dict[str, Any], row: Dict[str, str]) -> bytes:
    """
    Deep-copy the template, fill all placeholders from `row`,
    and return UTF-8 encoded JSON bytes ready to send.
    
    Supports array replication: if CSV has "<array_name>_count" column,
    array items will be replicated that many times.
    """
    filled = _fill_value(copy.deepcopy(template), row)
    return json.dumps(filled, ensure_ascii=False).encode("utf-8")


def get_placeholders(template: Dict[str, Any]) -> set:
    """
    Utility: extract all {{field}} names from a template.
    Useful for validating that input CSV has the required columns.
    """
    raw = json.dumps(template)
    return set(_PLACEHOLDER_RE.findall(raw))

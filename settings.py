"""
Central configuration for the API Automation Framework.
All tunables live here — no magic numbers scattered in code.
"""

import os

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
DATA_DIR        = BASE_DIR
TEMPLATE_DIR    = BASE_DIR
LOG_DIR         = os.path.join(BASE_DIR, "logs")
REPORT_DIR      = os.path.join(BASE_DIR, "reports")

INPUT_CSV       = os.path.join(DATA_DIR, "input_cases.csv")
EXPECTED_CSV    = os.path.join(DATA_DIR, "expected_output.csv")
REQUEST_TEMPLATE= os.path.join(TEMPLATE_DIR, "request_template.json")

PASS_LOG        = os.path.join(LOG_DIR, "pass.log")
FAIL_LOG        = os.path.join(LOG_DIR, "fail.log")
ERROR_LOG       = os.path.join(LOG_DIR, "error.log")
SUMMARY_REPORT  = os.path.join(REPORT_DIR, "summary.csv")

# ─── API ──────────────────────────────────────────────────────────────────────
# *** ONLY THIS LINE NEEDS TO BE CHANGED ***
API_URL = "http://localhost:8000/v1/transaction"

# Optional: add auth or custom headers if your API needs them
API_HEADERS = {
    "Content-Type": "application/json",
    "Accept":       "application/json",
    # "Authorization": "Bearer YOUR_TOKEN",   # uncomment if needed
}

API_TIMEOUT = 30    # seconds per request — increase if your API is slow

# ── Auto-parsed from API_URL — do not edit below this line ───────────────────
import urllib.parse as _up
_parsed       = _up.urlparse(API_URL)
API_USE_HTTPS = _parsed.scheme.lower() == "https"
API_HOST      = _parsed.hostname
API_PATH      = _parsed.path or "/"
API_PORT      = _parsed.port or (443 if API_USE_HTTPS else 80)

# ─── Execution ────────────────────────────────────────────────────────────────
BATCH_SIZE          = 500       # rows processed per batch before flushing logs
MAX_WORKERS         = 200      # threads for parallel execution
RETRY_COUNT         = 3         # retries on transient HTTP errors
RETRY_BACKOFF_SEC   = 2         # seconds to wait between retries (doubles each time)

# ─── Validation ───────────────────────────────────────────────────────────────
# Prefix that marks a column in expected CSV as "must validate this field"
EXPECTED_COL_PREFIX = "exp_"

# If True, a test PASSES even when non-critical fields mismatch
# Set to False for strict all-or-nothing validation
STRICT_VALIDATION   = True

# Fields that are allowed to differ (timestamps, trace IDs, etc.)
IGNORED_RESPONSE_FIELDS = {
    "timestamp",
    "trace_id",
    "request_id",
}

# ─── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL   = "INFO"   # DEBUG | INFO | WARNING | ERROR
LOG_TO_STDOUT = True   # also print to console while running

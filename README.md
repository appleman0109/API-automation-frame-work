# API Automation Framework
**Zero external dependencies · 5,00,000 test cases · Production-grade**

---

## Folder Structure

```
api_framework/
├── run.py                        ← Entry point. Run this.
├── config/
│   └── settings.py               ← All tunables (host, paths, threads, etc.)
├── core/
│   ├── csv_reader.py             ← Streaming CSV reader (O(1) memory)
│   ├── payload_builder.py        ← JSON template + {{placeholder}} filler
│   ├── http_client.py            ← http.client wrapper with retry + pooling
│   ├── validator.py              ← Actual vs expected comparison (dot-notation)
│   ├── reporter.py               ← Thread-safe CSV report + progress counter
│   └── executor.py               ← Orchestrates batch → thread pool → results
├── data/
│   ├── templates/
│   │   └── request_template.json ← Your API request skeleton
│   ├── input_cases.csv           ← Dynamic field values per test case
│   └── expected_output.csv       ← Expected response field values
├── logs/
│   ├── pass.log                  ← All passing test IDs
│   ├── fail.log                  ← All failures with field detail
│   ├── error.log                 ← HTTP/connection errors
│   └── framework.log             ← General execution log
├── reports/
│   └── summary.csv               ← One row per test: PASS/FAIL + details
└── tools/
    └── generate_test_data.py     ← Generate synthetic 5-lakh test data
```

---

## Quick Start

### 1. Configure your API
Edit `config/settings.py`:
```python
API_HOST      = "your-api-host.com"
API_PORT      = 443
API_PATH      = "/v1/your-endpoint"
API_USE_HTTPS = True
API_HEADERS   = {"Authorization": "Bearer YOUR_TOKEN", ...}
```

### 2. Set up your request template
Edit `data/templates/request_template.json`.
Use `{{field_name}}` placeholders for any dynamic field:
```json
{
  "customerId": "{{customer_id}}",
  "orderTotal": "{{total_amount}}",
  "staticField": "ALWAYS_THIS_VALUE"
}
```

### 3. Prepare your CSVs

**input_cases.csv** — One row per test. Column names match `{{placeholders}}`:
```
test_id, customer_id, total_amount, ...
TC_001,  CUST-1,      2500,         ...
```

**expected_output.csv** — Same row count. Columns prefixed `exp_` map to response paths:
```
test_id, exp_status, exp_order.totalAmount, exp_customer.tier
TC_001,  SUCCESS,    2500,                   GOLD
```
Dot-notation (`exp_order.totalAmount`) navigates nested JSON automatically.

### 4. Run

```bash
# Full run with defaults
python run.py

# Dry run — validates files/template, skips HTTP
python run.py --dry-run

# Custom parallelism
python run.py --workers 16 --batch 1000

# Custom file paths
python run.py --input /path/to/input.csv --expected /path/to/exp.csv
```

---

## Generating Test Data (for benchmarking)

```bash
python tools/generate_test_data.py --rows 500000
```
Writes streaming — flat memory regardless of row count. Takes ~60s for 5 lakh rows.

---

## Parallelism Design

```
CSV rows → batch (500 rows)
              ↓
     ThreadPoolExecutor (8 workers)
       ├── Worker 1: build → send → validate → log
       ├── Worker 2: build → send → validate → log
       ...
       └── Worker 8: build → send → validate → log
              ↓
     ReportWriter (thread-safe, streams to CSV)
```

- Each thread holds **its own persistent HTTP connection** — no connection-per-request overhead.
- Memory per batch: ~500 rows × ~1 KB = ~0.5 MB. Never more.
- Throughput at 8 workers: typically **200–800 tests/sec** depending on API latency.

### Scaling further (without external libs)

| Goal | Approach |
|------|----------|
| >8 cores | Increase `MAX_WORKERS` in settings.py |
| Multi-machine | Split input CSV, run `run.py` on each machine, merge reports |
| Process-level parallelism | Use `multiprocessing.Pool` (stdlib) to bypass Python GIL |

---

## Output Files

| File | Contents |
|------|----------|
| `logs/pass.log` | `PASS \| TC_001 \|` |
| `logs/fail.log` | `FAIL \| TC_002 \| field=order.status \| expected='CONFIRMED' \| actual='PENDING'` |
| `logs/error.log` | HTTP timeouts, connection errors |
| `reports/summary.csv` | test_id, status, http_status, total_checked, total_passed, failed_fields |

---

## Key Design Decisions

| Decision | Reason |
|----------|--------|
| Streaming CSV (no `readlines()`) | 5 lakh rows won't fit in RAM |
| `{{placeholder}}` templates | Safe, readable, no `eval()` |
| Per-thread HTTP connection | Avoids TCP handshake overhead per request |
| `exp_` column prefix | Cleanly separates metadata from assertions in one CSV |
| Dot-notation response access | Handles nested JSON without flattening |
| `concurrent.futures.ThreadPoolExecutor` | stdlib parallel I/O, no `multiprocessing` complexity |
| Batch + flush per row | Partial results survive mid-run crashes |

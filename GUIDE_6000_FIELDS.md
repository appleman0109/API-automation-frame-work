# Step-by-Step Guide: Handling 6000 Fields with Nested Structures

## Overview
Your API framework can handle ANY number of fields (6000, 60000+) with nested structures and arrays. Here's exactly how to set it up.

---

## Step 1: Organize Your Large Template

### Strategy: Organize by Modules
Instead of one flat template, organize into logical sections:

```json
{
  "metadata": {
    "transactionId": "{{transaction_id}}",
    "timestamp": "{{timestamp}}"
  },
  
  "customer": {
    "id": "{{customer_id}}",
    "profile": {
      "firstName": "{{first_name}}",
      "lastName": "{{last_name}}",
      "email": "{{email}}",
      "phone": "{{phone}}"
    },
    "address": {
      "line1": "{{addr_line1}}",
      "city": "{{addr_city}}"
    }
  },
  
  "order": {
    "id": "{{order_id}}",
    "items": [
      {
        "sku": "{{item1_sku}}",
        "quantity": "{{item1_qty}}",
        "price": "{{item1_price}}"
      },
      {
        "sku": "{{item2_sku}}",
        "quantity": "{{item2_qty}}",
        "price": "{{item2_price}}"
      }
    ]
  },
  
  "fields_section_1": {
    "field_1001": "{{field_1001}}",
    "field_1002": "{{field_1002}}",
    "field_1003": "{{field_1003}}"
  },
  
  "fields_section_2": {
    "field_2001": "{{field_2001}}",
    "field_2002": "{{field_2002}}",
    "field_2003": "{{field_2003}}"
  }
}
```

**Total template size:** ~100-200 KB JSON (easily handled)
**Payloads generated:** Each ~100-200 KB each (manageable)

---

## Step 2: Structure Your CSV

### For 6000 fields, create a WIDE CSV with columns:

```
test_id,transaction_id,timestamp,customer_id,first_name,...,field_6000
TC001,TXN001,2024-01-01T00:00:00Z,CUST001,John,...,value_6000
TC002,TXN002,2024-01-01T00:00:01Z,CUST002,Jane,...,value_6000
```

### CSV File Size Calculation:
- 6000 columns × 100 bytes average = **600 KB per row**
- 1000 rows × 600 KB = **600 MB CSV**
- Your framework handles this efficiently with streaming

### Tools to Create/Edit Wide CSVs:
1. **Python CSV generation script** (recommended)
2. **Excel** (but max ~16K columns)
3. **Google Sheets** with CSV export
4. **DuckDB** for SQL-based generation

---

## Step 3: Generate Payloads

### Option A: Generate Individual Request Files (Best for 6000+ fields)

```bash
python3 build_payloads.py request_template.json input_cases.csv requests --separate-files
```

**Output:** 1000 separate `.txt` files in `requests/` directory
- `TC_0000001.txt` (one request)
- `TC_0000002.txt` (one request)
- `TC_0000003.txt` (one request)
- ...
- `TC_1000000.txt` (one request)

**Advantages:**
✓ Each file is ~100-200 KB
✓ Easy to inspect individual requests
✓ Can process files in parallel
✓ Good for debugging specific test cases

### Option B: Generate JSONL (All in One File)

```bash
python3 build_payloads.py request_template.json input_cases.csv all_payloads.jsonl
```

**Output:** Single `all_payloads.jsonl` file
- Each line is one JSON payload
- File size: 1000 rows × 200 KB = **200 MB**

**Advantages:**
✓ Single file to manage
✓ Easy to stream and process
✓ Good for batch processing

---

## Step 4: Validate Your Payloads

### Check payload structure:

```bash
# View first request file
cat requests/TC_0000001.txt | python3 -m json.tool | head -50

# View first line of JSONL
head -1 all_payloads.jsonl | python3 -m json.tool | head -50

# Count total payloads
wc -l all_payloads.jsonl
ls requests/*.txt | wc -l
```

### Validate JSON syntax:

```bash
python3 -c "
import json, glob
for f in glob.glob('requests/*.txt')[:10]:  # Check first 10
    try:
        with open(f) as fp:
            json.load(fp)
        print(f'✓ {f}')
    except Exception as e:
        print(f'✗ {f}: {e}')
"
```

---

## Step 5: Integration with Your Framework

### A. Modify `executor.py` to use separate files:

```python
# Instead of:
# payloads from payload_builder

# Use:
import glob
import json

def run_all_from_files(request_dir="requests"):
    """Process individual request files."""
    files = sorted(glob.glob(f"{request_dir}/*.txt"))
    
    for file_path in files:
        with open(file_path) as f:
            payload = json.load(f)
        
        status, response = send_request(json.dumps(payload).encode('utf-8'))
        # Validate response...
```

### B. Process in Batches (for 6000 fields):

```python
def process_requests_in_batches(request_dir="requests", batch_size=100):
    """Process files in batches for efficient memory usage."""
    files = sorted(glob.glob(f"{request_dir}/*.txt"))
    
    for i in range(0, len(files), batch_size):
        batch = files[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}: {len(batch)} files")
        
        for file_path in batch:
            with open(file_path) as f:
                payload = json.load(f)
            # Send request
            # Validate response
```

---

## Step 6: Handle Memory for 6000+ Fields

### Problem: Large payloads consume memory
### Solutions:

#### 1. Stream Processing (Recommended)
```python
# Don't load all payloads into memory
for file_path in file_list:
    with open(file_path) as f:
        payload = json.load(f)  # Load one at a time
    send_request(payload)
    # Process immediately, don't store
```

#### 2. Increase Worker Threads Carefully
```python
# settings.py
MAX_WORKERS = 50  # Start conservative with large payloads
# Too many workers = Out of memory
# Too few = Slow execution

# Rule of thumb:
# Payload size (MB) * Workers = Available RAM
# 200 MB payload × 50 workers = 10 GB needed
```

#### 3. Use JSONL with Streaming
```bash
# Process JSONL line by line (no loading entire file)
cat all_payloads.jsonl | parallel --pipe python3 process_payload.py
```

---

## Step 7: Validation with 6000 Fields

### Strategy: Test a Subset First

**CSV for quick validation:**
```
test_id,transaction_id,customer_id,...,field_6000
TC001,TXN001,CUST001,...,value_6000
TC002,TXN002,CUST002,...,value_6000
```

Only 2-3 rows for initial testing.

**Expected output:**
```csv
test_id,exp_customer_id,exp_order_id,exp_field_5000,exp_field_6000
TC001,CUST001,ORD001,expected_value,expected_value
TC002,CUST002,ORD002,expected_value,expected_value
```

---

## Step 8: Performance Tips for Large Payloads

| Parameter | For 6000 Fields | Notes |
|-----------|-----------------|-------|
| `BATCH_SIZE` | 50-100 | Smaller batches = more frequent logs |
| `MAX_WORKERS` | 20-50 | Conservative with large payloads |
| `API_TIMEOUT` | 60+ sec | Large payloads take longer to process |
| `RETRY_COUNT` | 3-5 | More retries = better reliability |
| File format | Separate `.txt` files | Better than JSONL for large payloads |

---

## Step 9: Example Workflow for 6000 Fields

```bash
# 1. Create template with 6000 placeholders
vim request_template.json

# 2. Create CSV with 6000 columns + 1000 test cases
python3 generate_large_csv.py

# 3. Generate individual request files
python3 build_payloads.py request_template.json input_6000.csv requests --separate-files

# 4. Validate sample requests
cat requests/TC_0000001.txt | python3 -m json.tool | head -30

# 5. Run the full framework
python3 run.py --input input_6000.csv --template request_template.json --workers 30

# 6. Review results
ls -lh reports/
cat logs/pass.log | wc -l
cat logs/fail.log | head -20
```

---

## Step 10: Common Issues & Solutions

### Issue 1: CSV Too Large (> 1GB)
**Solution:** Split into multiple smaller CSVs
```bash
split -l 100 large_input.csv input_part_
# Run each part separately
```

### Issue 2: Out of Memory
**Solution:** Reduce `MAX_WORKERS` or process in smaller batches
```python
MAX_WORKERS = 10  # Was 200, now 10
```

### Issue 3: Slow Payload Generation
**Solution:** Template is too complex, simplify or use JSON columns
```python
# Instead of 6000 placeholders:
# Use JSON column for large nested sections
"items": "{{items_json}}"  # One column with full JSON array
```

### Issue 4: Validation Too Slow
**Solution:** Validate a subset of fields
```python
# Don't validate all 6000 fields
# Only validate critical fields (20-30)
IGNORED_RESPONSE_FIELDS = ["field_1001", "field_1002", ...]
```

---

## Checklist for 6000 Fields Implementation

- [ ] Template created with all 6000 placeholders organized by modules
- [ ] CSV generated with all 6000 columns + test data
- [ ] Payload builder tested on sample (2-3 rows)
- [ ] Generated requests validated for JSON syntax
- [ ] Memory usage profiled for your environment
- [ ] `settings.py` tuned for large payloads
- [ ] `MAX_WORKERS` set conservatively (20-50)
- [ ] Full run executed on complete dataset
- [ ] Results reviewed and logged
- [ ] Performance metrics collected

---

## Summary

Your framework **CAN handle 6000+ fields** because:
1. ✅ **Recursive placeholder substitution** - No limit on field count
2. ✅ **Streaming payloads** - Each processed independently
3. ✅ **Individual file storage** - No memory overload
4. ✅ **Multi-threaded execution** - Parallel request sending
5. ✅ **Flexible validation** - Can validate subset or all fields

**Key for success:** Use **separate `.txt` files** instead of one giant JSONL for payloads > 500 MB.

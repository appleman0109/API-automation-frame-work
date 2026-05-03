#!/usr/bin/env python3
"""
Test script: Dynamic Array Replication Example
Shows how a single template object can create multiple array items.
"""

import json
import sys
sys.path.insert(0, '/Users/amanverma/Desktop/files 2')

from payload_builder import load_template, build_payload
from csv_reader import iter_batches

# Load template with single array items
template = load_template('/Users/amanverma/Desktop/files 2/example_dynamic_array_template.json')

print("=" * 80)
print("TEMPLATE (single item per array):")
print(json.dumps(template, indent=2))
print("=" * 80)

# Process CSV rows
input_file = '/Users/amanverma/Desktop/files 2/example_dynamic_array_input.csv'

for batch in iter_batches(input_file, batch_size=1):
    for row in batch:
        print(f"\n\nCSV ROW #{row.get('test_id', 'N/A')}:")
        print(f"  order_id: {row['order_id']}")
        print(f"  item_sku: {row['item_sku']}")
        print(f"  items_count: {row['items_count']}")
        print(f"  shippingOptions_count: {row['shippingOptions_count']}")
        
        # Build payload
        payload_bytes = build_payload(template, row)
        payload_dict = json.loads(payload_bytes.decode('utf-8'))
        
        print(f"\nGENERATED PAYLOAD:")
        print(json.dumps(payload_dict, indent=2))
        
        print(f"\n✓ Items array has {len(payload_dict['items'])} items (replicated {row['items_count']} times)")
        print(f"✓ ShippingOptions array has {len(payload_dict['shippingOptions'])} items (replicated {row['shippingOptions_count']} times)")

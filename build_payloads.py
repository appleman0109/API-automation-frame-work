#!/usr/bin/env python3
"""
Standalone Payload Builder
Reads JSON template + CSV input → generates JSON request payloads.
No HTTP, no validation — just pure payload generation.

Usage:
    python build_payloads.py <template.json> <input.csv> [output.jsonl]
"""

import json
import csv
import sys
import os
import re
import copy
from typing import Dict, Any
from pathlib import Path


class PayloadBuilder:
    """Builds JSON payloads from template + CSV rows."""
    
    def __init__(self, template_path: str):
        """Load and validate template."""
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            self.template = json.load(f)
        
        self.placeholder_pattern = re.compile(r'\{\{(\w+)\}\}')
        print(f"✓ Template loaded: {template_path}")
    
    def _coerce(self, value: str) -> Any:
        """Convert string to appropriate type."""
        if value == "" or value is None:
            return None
        
        # Try int
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Try boolean
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        
        return value
    
    def _fill_value(self, value: Any, row: Dict[str, str]) -> Any:
        """Recursively fill placeholders in value."""
        if isinstance(value, str):
            # Full match: {{placeholder}} → type coercion
            full_match = self.placeholder_pattern.fullmatch(value)
            if full_match:
                key = full_match.group(1)
                raw = row.get(key, "")
                return self._coerce(raw)
            
            # Partial match: "text {{placeholder}} more" → string substitution
            def replacer(m):
                return str(row.get(m.group(1), ""))
            return self.placeholder_pattern.sub(replacer, value)
        
        elif isinstance(value, dict):
            return {k: self._fill_value(v, row) for k, v in value.items()}
        
        elif isinstance(value, list):
            return [self._fill_value(item, row) for item in value]
        
        return value
    
    def build(self, row: Dict[str, str]) -> Dict[str, Any]:
        """Build payload for one CSV row."""
        filled = self._fill_value(copy.deepcopy(self.template), row)
        return filled
    
    def build_from_csv(self, csv_path: str, output_path: str = None):
        """
        Read CSV file and generate payloads for each row.
        
        Args:
            csv_path: Path to input CSV
            output_path: Optional path to save as JSONL (one JSON per line)
        
        Returns:
            List of generated payloads
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV not found: {csv_path}")
        
        payloads = []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row_count = 0
            
            for row_num, row in enumerate(reader, start=2):  # +2: header is line 1
                try:
                    payload = self.build(row)
                    payloads.append(payload)
                    row_count += 1
                except Exception as e:
                    print(f"⚠ Error building row {row_num}: {e}")
        
        print(f"✓ Built {row_count} payloads from {csv_path}")
        
        # Save to JSONL if output path provided
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                for payload in payloads:
                    f.write(json.dumps(payload, ensure_ascii=False) + '\n')
            print(f"✓ Payloads saved to: {output_path}")
        
        return payloads
    
    def build_from_csv_to_files(self, csv_path: str, output_dir: str):
        """
        Read CSV file and save each payload as a separate text file.
        
        Args:
            csv_path: Path to input CSV
            output_dir: Directory to save individual JSON files
        
        Returns:
            List of generated payloads
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV not found: {csv_path}")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        payloads = []
        file_paths = []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row_count = 0
            
            for row_num, row in enumerate(reader, start=2):  # +2: header is line 1
                try:
                    payload = self.build(row)
                    payloads.append(payload)
                    
                    # Extract test_id or use row number for filename
                    test_id = row.get('test_id', f'request_{row_num}')
                    filename = f"{test_id}.txt"
                    filepath = os.path.join(output_dir, filename)
                    
                    # Save as formatted JSON text file
                    with open(filepath, 'w', encoding='utf-8') as tf:
                        tf.write(json.dumps(payload, indent=2, ensure_ascii=False))
                    
                    file_paths.append(filepath)
                    row_count += 1
                    
                except Exception as e:
                    print(f"⚠ Error building row {row_num}: {e}")
        
        print(f"✓ Built {row_count} payloads from {csv_path}")
        print(f"✓ Saved {len(file_paths)} request files to: {output_dir}")
        
        return payloads


def main():
    """CLI interface."""
    if len(sys.argv) < 3:
        print("Usage: python build_payloads.py <template.json> <input.csv> [output.jsonl] [--separate-files]")
        print()
        print("Examples:")
        print("  python build_payloads.py request_template.json input_cases.csv payloads.jsonl")
        print("  python build_payloads.py request_template.json input_cases.csv payloads --separate-files")
        print("  python build_payloads.py template.json data.csv")
        sys.exit(1)
    
    template_path = sys.argv[1]
    csv_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else None
    separate_files = '--separate-files' in sys.argv or '-s' in sys.argv
    
    try:
        builder = PayloadBuilder(template_path)
        
        if separate_files:
            # Save each payload as separate text file
            output_dir = output_path or "payloads"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            payloads = builder.build_from_csv_to_files(csv_path, output_dir)
        else:
            # Save as JSONL (default)
            payloads = builder.build_from_csv(csv_path, output_path)
        
        print()
        print("=" * 60)
        print("First payload preview:")
        print("=" * 60)
        if payloads:
            print(json.dumps(payloads[0], indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

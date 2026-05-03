#!/usr/bin/env python3
"""
tools/generate_test_data.py

Generates synthetic input_cases.csv and expected_output.csv
for load testing (default: 500,000 rows).

Usage:
    python tools/generate_test_data.py --rows 500000
    python tools/generate_test_data.py --rows 1000 --output-dir data/

Writes files incrementally — memory usage stays flat regardless of row count.
Only built-ins: csv, random, argparse, os, sys, datetime.
"""

import argparse
import csv
import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from settings import DATA_DIR

TIERS    = ["BRONZE", "SILVER", "GOLD", "PLATINUM"]
CHANNELS = ["WEB", "APP", "MOBILE", "KIOSK"]
METHODS  = ["CARD", "UPI", "NETBANK", "WALLET"]
CURRENCY = ["INR", "USD", "EUR", "GBP"]
SKUS     = [f"SKU-{chr(65+i)}{i+1}" for i in range(20)]
STATES   = ["MH", "KA", "TN", "TS", "DL", "GJ", "RJ", "UP", "WB", "KL"]
RISK     = ["LOW", "MEDIUM"]

INPUT_HEADERS = [
    "test_id","transaction_id","request_timestamp","customer_id",
    "first_name","last_name","email","phone_number","customer_tier",
    "order_id","currency","total_amount","discount_code","channel",
    "item_sku","item_quantity","item_unit_price",
    "shipping_line1","shipping_city","shipping_state","shipping_postcode","shipping_country",
    "payment_method","card_last_four","billing_zip"
]

EXPECTED_HEADERS = [
    "test_id",
    "exp_status","exp_statusCode",
    "exp_order.orderId","exp_order.status","exp_order.currency","exp_order.totalAmount",
    "exp_customer.customerId","exp_customer.tier",
    "exp_payment.status","exp_payment.method",
    "exp_flags.emailSent","exp_flags.inventoryReserved",
    "exp_riskScore","exp_message"
]


def _row(i: int, base_dt: datetime):
    tier     = random.choice(TIERS)
    method   = random.choice(METHODS)
    currency = random.choice(CURRENCY)
    sku      = random.choice(SKUS)
    qty      = random.randint(1, 5)
    price    = round(random.uniform(100, 5000), 2)
    total    = round(qty * price, 2)
    state    = random.choice(STATES)
    ts       = (base_dt + timedelta(seconds=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
    postcode = str(random.randint(100000, 999999))
    card4    = str(random.randint(1000, 9999)) if method == "CARD" else ""
    disc     = random.choice(["", "DISC10", "SAVE5", "PLAT20", ""])

    inp = {
        "test_id":           f"TC_{i:07d}",
        "transaction_id":    f"TXN-{i:08d}",
        "request_timestamp": ts,
        "customer_id":       f"CUST-{i:07d}",
        "first_name":        f"User{i}",
        "last_name":         f"Test",
        "email":             f"user{i}@test.com",
        "phone_number":      f"+91{random.randint(7000000000, 9999999999)}",
        "customer_tier":     tier,
        "order_id":          f"ORD-{i:08d}",
        "currency":          currency,
        "total_amount":      total,
        "discount_code":     disc,
        "channel":           random.choice(CHANNELS),
        "item_sku":          sku,
        "item_quantity":     qty,
        "item_unit_price":   price,
        "shipping_line1":    f"{i} Test Street",
        "shipping_city":     "Mumbai",
        "shipping_state":    state,
        "shipping_postcode": postcode,
        "shipping_country":  "IN",
        "payment_method":    method,
        "card_last_four":    card4,
        "billing_zip":       postcode,
    }

    exp = {
        "test_id":                    f"TC_{i:07d}",
        "exp_status":                 "SUCCESS",
        "exp_statusCode":             "200",
        "exp_order.orderId":          f"ORD-{i:08d}",
        "exp_order.status":           "CONFIRMED",
        "exp_order.currency":         currency,
        "exp_order.totalAmount":      str(total),
        "exp_customer.customerId":    f"CUST-{i:07d}",
        "exp_customer.tier":          tier,
        "exp_payment.status":         "CAPTURED",
        "exp_payment.method":         method,
        "exp_flags.emailSent":        "true",
        "exp_flags.inventoryReserved":"true",
        "exp_riskScore":              random.choice(RISK),
        "exp_message":                "Order placed successfully",
    }
    return inp, exp


def generate(rows: int, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    inp_path = os.path.join(output_dir, "input_cases.csv")
    exp_path = os.path.join(output_dir, "expected_output.csv")
    base_dt  = datetime(2024, 1, 1, 0, 0, 0)

    print(f"Generating {rows:,} test cases...")
    with (
        open(inp_path, "w", newline="", encoding="utf-8") as inf,
        open(exp_path, "w", newline="", encoding="utf-8") as expf
    ):
        iw = csv.DictWriter(inf,  fieldnames=INPUT_HEADERS)
        ew = csv.DictWriter(expf, fieldnames=EXPECTED_HEADERS)
        iw.writeheader()
        ew.writeheader()

        for i in range(1, rows + 1):
            inp, exp = _row(i, base_dt)
            iw.writerow(inp)
            ew.writerow(exp)
            if i % 50_000 == 0:
                print(f"  {i:,} rows written...")

    print(f"\nDone.")
    print(f"  Input    : {inp_path}")
    print(f"  Expected : {exp_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows",       type=int, default=500_000)
    parser.add_argument("--output-dir", default=DATA_DIR)
    args = parser.parse_args()
    generate(args.rows, args.output_dir)

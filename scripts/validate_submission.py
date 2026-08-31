#!/usr/bin/env python3
"""
validate_submission.py — Validate a reconciliation submission CSV.

Checks:
  1. Correct columns (invoice_number, status)
  2. Correct row count (matches input invoices)
  3. No duplicate invoice numbers
  4. All statuses are valid
  5. Optional: compare against reference submission
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

VALID_STATUSES = {
    "CLEAN", "QTY_MISMATCH", "RATE_MISMATCH", "DUPLICATE_INVOICE",
    "MISSING_PO", "VENDOR_MISMATCH", "GST_ERROR", "UOM_MISMATCH",
}


def validate(submission_path: str, invoices_path: str, reference_path: str | None = None):
    sub = pd.read_csv(submission_path)
    inv = pd.read_csv(invoices_path)

    errors = []
    warnings = []

    # Column check
    expected_cols = ["invoice_number", "status"]
    if list(sub.columns) != expected_cols:
        errors.append(f"Expected columns {expected_cols}, got {list(sub.columns)}")

    # Row count
    if len(sub) != len(inv):
        errors.append(f"Row count mismatch: submission={len(sub)}, invoices={len(inv)}")

    # Unique invoice numbers
    if sub["invoice_number"].duplicated().any():
        dups = sub[sub["invoice_number"].duplicated()]["invoice_number"].tolist()
        errors.append(f"Duplicate invoice numbers: {dups[:5]}")

    # All invoices present
    missing = set(inv["invoice_number"]) - set(sub["invoice_number"])
    if missing:
        errors.append(f"Missing invoices in submission: {sorted(list(missing))[:5]}")

    extra = set(sub["invoice_number"]) - set(inv["invoice_number"])
    if extra:
        errors.append(f"Extra invoices in submission: {sorted(list(extra))[:5]}")

    # Valid statuses
    invalid = set(sub["status"].unique()) - VALID_STATUSES
    if invalid:
        errors.append(f"Invalid statuses: {invalid}")

    # Status distribution
    print("Status distribution:")
    print(sub["status"].value_counts().to_string())
    print()

    if errors:
        print("[FAIL] VALIDATION FAILED:")
        for e in errors:
            print(f"  ERROR: {e}")
    else:
        print("[PASS] All validations passed.")

    # Compare to reference
    if reference_path:
        ref = pd.read_csv(reference_path)
        merged = sub.merge(ref, on="invoice_number", suffixes=("_new", "_ref"))
        changed = merged[merged["status_new"] != merged["status_ref"]]
        if len(changed) > 0:
            print(f"\n[WARN] {len(changed)} classifications differ from reference:")
            for _, row in changed.iterrows():
                print(f"  {row['invoice_number']}: {row['status_ref']} -> {row['status_new']}")
        else:
            print(f"\n[PASS] All {len(merged)} classifications match reference.")

    return len(errors) == 0


def main():
    parser = argparse.ArgumentParser(description="Validate reconciliation submission")
    parser.add_argument("submission", help="Path to submission CSV")
    parser.add_argument("--invoices", default="data/vendor_invoices.csv", help="Path to invoices CSV")
    parser.add_argument("--reference", default=None, help="Path to reference submission CSV for comparison")
    args = parser.parse_args()

    ok = validate(args.submission, args.invoices, args.reference)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

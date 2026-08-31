#!/usr/bin/env python3
"""
validate_all_outputs.py — Pre-submission validator for Reconciliation and Knowledge submission files.

Validates:
1. Reconciliation submission:
   - File exists and is valid UTF-8 CSV
   - Exact columns: ['invoice_number', 'status']
   - Expected row count matches dataset invoices (250)
   - Unique invoice numbers
   - All status values belong to allowed 8 statuses:
     CLEAN, QTY_MISMATCH, RATE_MISMATCH, DUPLICATE_INVOICE, MISSING_PO, VENDOR_MISMATCH, GST_ERROR, UOM_MISMATCH
2. Knowledge submission (if present):
   - File exists and is valid UTF-8 CSV
   - Exact columns: ['qid', 'answer', 'governing_source']
   - Unique QIDs
   - Non-empty answers and governing sources
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
import pandas as pd

ALLOWED_RECON_STATUSES = {
    "CLEAN",
    "QTY_MISMATCH",
    "RATE_MISMATCH",
    "DUPLICATE_INVOICE",
    "MISSING_PO",
    "VENDOR_MISMATCH",
    "GST_ERROR",
    "UOM_MISMATCH",
}


def validate_reconciliation(recon_path: Path, invoices_path: Path) -> list[str]:
    errors = []
    if not recon_path.exists():
        return [f"Reconciliation submission file not found: {recon_path}"]

    try:
        df_sub = pd.read_csv(recon_path, encoding="utf-8")
    except Exception as e:
        return [f"Failed to parse reconciliation CSV as UTF-8: {e}"]

    # Columns
    expected_cols = ["invoice_number", "status"]
    if list(df_sub.columns) != expected_cols:
        errors.append(f"Invalid columns {list(df_sub.columns)}, expected {expected_cols}")

    # Row count & uniqueness
    if invoices_path.exists():
        df_inv = pd.read_csv(invoices_path)
        if len(df_sub) != len(df_inv):
            errors.append(f"Row count mismatch: submission={len(df_sub)}, expected={len(df_inv)}")
        missing_inv = set(df_inv["invoice_number"]) - set(df_sub["invoice_number"])
        if missing_inv:
            errors.append(f"Missing {len(missing_inv)} invoices in submission: {list(missing_inv)[:5]}")

    if df_sub["invoice_number"].duplicated().any():
        dupes = df_sub[df_sub["invoice_number"].duplicated()]["invoice_number"].tolist()
        errors.append(f"Duplicate invoice numbers present: {dupes[:5]}")

    # Allowed statuses
    invalid_statuses = set(df_sub["status"].unique()) - ALLOWED_RECON_STATUSES
    if invalid_statuses:
        errors.append(f"Invalid status values found: {invalid_statuses}")

    return errors


def validate_knowledge(know_path: Path) -> list[str]:
    errors = []
    if not know_path.exists():
        return [f"Knowledge submission file not found: {know_path}"]

    try:
        df_k = pd.read_csv(know_path, encoding="utf-8")
    except Exception as e:
        return [f"Failed to parse knowledge CSV as UTF-8: {e}"]

    expected_cols = ["qid", "answer", "governing_source"]
    if list(df_k.columns) != expected_cols:
        errors.append(f"Invalid columns {list(df_k.columns)}, expected {expected_cols}")

    if df_k["qid"].duplicated().any():
        errors.append("Duplicate QIDs present in knowledge submission")

    if df_k["answer"].isna().any():
        errors.append("Found null/blank answers in knowledge submission")

    if df_k["governing_source"].isna().any():
        errors.append("Found null/blank governing_source in knowledge submission")

    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate all competition submission outputs")
    parser.add_argument("--recon", default="outputs/reconciliation_submission.csv", help="Reconciliation CSV")
    parser.add_argument("--invoices", default="data/vendor_invoices.csv", help="Invoices CSV reference")
    parser.add_argument("--knowledge", default="knowledge_submission.csv", help="Knowledge CSV")
    args = parser.parse_args()

    print("==================================================")
    print("SUBMISSION OUTPUTS VALIDATION")
    print("==================================================")

    # 1. Validate Reconciliation
    recon_p = Path(args.recon)
    inv_p = Path(args.invoices)
    print(f"Checking Reconciliation Submission: {recon_p}")
    recon_errs = validate_reconciliation(recon_p, inv_p)
    if recon_errs:
        print("[FAIL] Reconciliation Errors:")
        for e in recon_errs:
            print(f"  - {e}")
    else:
        print("[PASS] Reconciliation submission is 100% valid.")

    # 2. Validate Knowledge (if file exists)
    know_p = Path(args.knowledge)
    if know_p.exists():
        print(f"\nChecking Knowledge Submission: {know_p}")
        know_errs = validate_knowledge(know_p)
        if know_errs:
            print("[FAIL] Knowledge Errors:")
            for e in know_errs:
                print(f"  - {e}")
        else:
            print("[PASS] Knowledge submission is 100% valid.")

    total_errors = len(recon_errs)
    if total_errors > 0:
        print(f"\n[FAIL] Validation completed with {total_errors} errors.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All validated submission outputs passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()

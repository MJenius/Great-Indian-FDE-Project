#!/usr/bin/env python3
"""
run_reconciliation.py — Run the full reconciliation engine against the dataset.

Usage:
    python scripts/run_reconciliation.py --data-dir data --output-dir outputs
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.reconciliation.loader import load_datasets
from src.reconciliation.classifier import classify_all, results_to_submission
from src.reconciliation.diagnostics import build_diagnostics_df, print_summary


def main():
    parser = argparse.ArgumentParser(description="Run DRI Reconciliation Engine")
    parser.add_argument("--data-dir", default="data", help="Directory containing CSV files")
    parser.add_argument("--output-dir", default="outputs", help="Directory for output files")
    parser.add_argument("--rate-tolerance", type=float, default=0.01, help="Rate comparison tolerance")
    parser.add_argument("--gst-tolerance", type=float, default=0.05, help="GST comparison tolerance")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load and validate
    print("Loading datasets...")
    load_result = load_datasets(data_dir)

    if load_result.issues:
        print(f"\nValidation issues ({len(load_result.issues)}):")
        for issue in load_result.issues:
            print(f"  [{issue.severity}] [{issue.dataset}] {issue.message}")

    load_result.raise_if_errors()
    print(f"  Invoices: {len(load_result.invoices)} rows")
    print(f"  POs: {len(load_result.purchase_orders)} rows")
    print(f"  Vendors: {len(load_result.vendors)} rows")
    print(f"  Products: {len(load_result.products)} rows")

    # 2. Classify
    print("\nClassifying invoices...")
    results = classify_all(
        invoices=load_result.invoices,
        purchase_orders=load_result.purchase_orders,
        vendors=load_result.vendors,
        rate_tolerance=args.rate_tolerance,
        gst_tolerance=args.gst_tolerance,
    )

    # 3. Output
    submission = results_to_submission(results)
    submission_path = output_dir / "reconciliation_submission.csv"
    submission.to_csv(submission_path, index=False)
    print(f"\nSubmission written: {submission_path} ({len(submission)} rows)")

    diagnostics = build_diagnostics_df(results, load_result.invoices)
    diag_path = output_dir / "reconciliation_diagnostics.csv"
    diagnostics.to_csv(diag_path, index=False)
    print(f"Diagnostics written: {diag_path} ({len(diagnostics)} rows)")

    # 4. Summary
    print_summary(results, load_result.invoices)

    # 5. Validation checks
    print("OUTPUT VALIDATION:")
    assert len(submission) == len(load_result.invoices), \
        f"Row count mismatch: {len(submission)} vs {len(load_result.invoices)}"
    print(f"  [OK] Row count: {len(submission)}")

    assert submission["invoice_number"].is_unique, "Duplicate invoice numbers in output"
    print(f"  [OK] Unique invoice numbers")

    from src.reconciliation.classifier import VALID_STATUSES
    unexpected = set(submission["status"].unique()) - VALID_STATUSES
    assert not unexpected, f"Unexpected statuses: {unexpected}"
    print(f"  [OK] All statuses valid")

    assert list(submission.columns) == ["invoice_number", "status"], \
        f"Unexpected columns: {list(submission.columns)}"
    print(f"  [OK] Correct column headers")

    print("\n[PASS] All output validations passed.")


if __name__ == "__main__":
    main()

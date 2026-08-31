"""
diagnostics.py — Diagnostic output generation for reconciliation results.

Produces:
  1. Full diagnostic CSV with raw flags and validator evidence per invoice.
  2. Summary statistics by class.
  3. Value-at-risk calculation.
"""
from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd


def build_diagnostics_df(
    results: List[Dict[str, Any]],
    invoices: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build a comprehensive diagnostic DataFrame from classification results.

    Each row contains the invoice fields plus:
      - status: final classification
      - raw_*: boolean raw flags for each check
      - reason: human-readable reason for the final classification
    """
    inv_indexed = invoices.set_index("invoice_number")

    records = []
    for r in results:
        inv_num = r["invoice_number"]
        resolution = r["resolution"]
        raw_flags = resolution.get("raw_flags", {})

        # Start with original invoice fields
        row_data = {}
        if inv_num in inv_indexed.index:
            row_data = inv_indexed.loc[inv_num].to_dict()

        row_data["invoice_number"] = inv_num
        row_data["status"] = r["status"]
        row_data["reason"] = resolution.get("reason", "")

        # Raw flags
        row_data["raw_missing_po"] = raw_flags.get("MISSING_PO", False)
        row_data["raw_vendor_mismatch"] = raw_flags.get("VENDOR_MISMATCH", False)
        row_data["raw_uom_mismatch"] = raw_flags.get("UOM_MISMATCH", False)
        row_data["raw_qty_mismatch"] = raw_flags.get("QTY_MISMATCH", False)
        row_data["raw_rate_mismatch"] = raw_flags.get("RATE_MISMATCH", False)
        row_data["raw_gst_error"] = raw_flags.get("GST_ERROR", False)
        row_data["raw_duplicate"] = raw_flags.get("DUPLICATE_INVOICE", False)

        # Count of raw flags
        row_data["raw_flag_count"] = sum(1 for v in raw_flags.values() if v)

        records.append(row_data)

    df = pd.DataFrame(records)

    # Reorder columns: invoice_number first, status second, then original cols, then diagnostics
    priority_cols = ["invoice_number", "status", "reason"]
    diag_cols = [c for c in df.columns if c.startswith("raw_")]
    other_cols = [c for c in df.columns if c not in priority_cols and c not in diag_cols]
    ordered = priority_cols + other_cols + diag_cols
    df = df[[c for c in ordered if c in df.columns]]

    return df


def print_summary(results: List[Dict[str, Any]], invoices: pd.DataFrame):
    """Print a human-readable summary of classification results."""
    statuses = [r["status"] for r in results]
    counts = pd.Series(statuses).value_counts()

    # Value at risk
    inv_indexed = invoices.set_index("invoice_number")
    value_by_class: Dict[str, float] = {}
    for r in results:
        status = r["status"]
        inv_num = r["invoice_number"]
        if status != "CLEAN" and inv_num in inv_indexed.index:
            total = inv_indexed.loc[inv_num, "invoice_total"]
            value_by_class[status] = value_by_class.get(status, 0) + total

    print("=" * 60)
    print("RECONCILIATION SUMMARY")
    print("=" * 60)
    print(f"Total invoices: {len(results)}")
    print(f"Clean: {counts.get('CLEAN', 0)}")
    print(f"Exceptions: {len(results) - counts.get('CLEAN', 0)}")
    print()
    print(f"{'Status':<25} {'Count':>6} {'Value at Risk':>18}")
    print("-" * 52)

    for status in ["CLEAN", "MISSING_PO", "VENDOR_MISMATCH", "UOM_MISMATCH",
                    "QTY_MISMATCH", "RATE_MISMATCH", "GST_ERROR", "DUPLICATE_INVOICE"]:
        cnt = counts.get(status, 0)
        val = value_by_class.get(status, 0)
        val_str = f"INR {val:,.2f}" if val > 0 else "--"
        print(f"{status:<25} {cnt:>6} {val_str:>20}")

    total_risk = sum(value_by_class.values())
    print("-" * 54)
    print(f"{'Total value at risk':<25} {'':>6} {'INR ' + f'{total_risk:,.2f}':>20}")
    print()

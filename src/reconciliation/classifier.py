"""
classifier.py — The main reconciliation classifier.

Orchestrates:
  1. PO resolution (exact match)
  2. Running all validators against each invoice
  3. Duplicate detection across the full invoice set
  4. Precedence resolution to produce the final classification
  5. Collecting structured diagnostics for every row
"""
from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from .normalization import normalize_po_reference
from .resolver import resolve_classification
from .validators import (
    validate_duplicate,
    validate_gst,
    validate_po_exists,
    validate_quantity,
    validate_rate,
    validate_uom,
    validate_vendor,
)


VALID_STATUSES = frozenset([
    "CLEAN", "QTY_MISMATCH", "RATE_MISMATCH", "DUPLICATE_INVOICE",
    "MISSING_PO", "VENDOR_MISMATCH", "GST_ERROR", "UOM_MISMATCH",
])


def _build_po_lookup(po_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Build a dict mapping po_number -> PO row dict for O(1) lookups."""
    lookup = {}
    for _, row in po_df.iterrows():
        po_num = normalize_po_reference(row["po_number"])
        lookup[po_num] = row.to_dict()
    return lookup


def _build_vendor_lookup(vendor_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Build a dict mapping vendor_id -> vendor record for diagnostic enrichment."""
    lookup = {}
    for _, row in vendor_df.iterrows():
        lookup[row["vendor_id"]] = row.to_dict()
    return lookup


def _build_po_invoice_groups(inv_df: pd.DataFrame) -> Dict[str, List[dict]]:
    """Group invoices by PO number for duplicate detection."""
    groups: Dict[str, List[dict]] = {}
    for _, row in inv_df.iterrows():
        po = normalize_po_reference(row["po_number"])
        entry = {
            "invoice_number": row["invoice_number"],
            "invoice_date": row["invoice_date"],
        }
        groups.setdefault(po, []).append(entry)
    return groups


def classify_invoice(
    inv_row: dict,
    po_lookup: Dict[str, Dict],
    vendor_lookup: Dict[str, Dict],
    po_invoice_groups: Dict[str, List[dict]],
    rate_tolerance: float = 0.01,
    gst_tolerance: float = 0.05,
    precedence: list | None = None,
) -> Dict[str, Any]:
    """
    Classify a single invoice row.

    Returns a dict with:
        - "invoice_number": str
        - "status": str (one of VALID_STATUSES)
        - "validation_results": dict of all check results
        - "resolution": dict from the resolver
    """
    inv_num = inv_row["invoice_number"]
    po_num = normalize_po_reference(inv_row["po_number"])

    validation_results: Dict[str, Any] = {}

    # 1. PO existence
    po_check = validate_po_exists(po_num, po_lookup)
    validation_results["po_exists"] = po_check

    if not po_check["passed"]:
        # No PO -> skip all further checks
        resolution = resolve_classification(validation_results, precedence)
        return {
            "invoice_number": inv_num,
            "status": resolution["status"],
            "validation_results": validation_results,
            "resolution": resolution,
        }

    po_row = po_lookup[po_num]

    # 2. Vendor
    vendor_check = validate_vendor(
        invoice_vendor_id=inv_row["vendor_id"],
        po_vendor_id=po_row["vendor_id"],
        vendor_master=vendor_lookup,
    )
    validation_results["vendor"] = vendor_check

    # 3. UOM
    uom_check = validate_uom(
        invoice_uom=inv_row["uom"],
        po_uom=po_row["uom"],
    )
    validation_results["uom"] = uom_check

    # 4. Quantity (UOM-aware)
    qty_check = validate_quantity(
        invoice_qty=float(inv_row["qty"]),
        po_qty=float(po_row["qty"]),
        uom_result=uom_check,
    )
    validation_results["quantity"] = qty_check

    # 5. Rate (UOM-aware)
    rate_check = validate_rate(
        invoice_rate=float(inv_row["rate"]),
        po_rate=float(po_row["rate"]),
        tolerance=rate_tolerance,
        uom_result=uom_check,
    )
    validation_results["rate"] = rate_check

    # 6. GST
    gst_check = validate_gst(
        taxable_value=float(inv_row["taxable_value"]),
        gst_rate_pct=float(inv_row["gst_rate_pct"]),
        gst_amount=float(inv_row["gst_amount"]),
        tolerance=gst_tolerance,
    )
    validation_results["gst"] = gst_check

    # 7. Duplicate (needs context of all invoices for this PO)
    all_for_po = po_invoice_groups.get(po_num, [])
    dup_check = validate_duplicate(
        invoice_number=inv_num,
        invoice_date=inv_row["invoice_date"],
        po_number=po_num,
        all_invoices_for_po=all_for_po,
    )
    validation_results["duplicate"] = dup_check

    # 8. Resolve
    resolution = resolve_classification(validation_results, precedence)

    return {
        "invoice_number": inv_num,
        "status": resolution["status"],
        "validation_results": validation_results,
        "resolution": resolution,
    }


def classify_all(
    invoices: pd.DataFrame,
    purchase_orders: pd.DataFrame,
    vendors: pd.DataFrame,
    rate_tolerance: float = 0.01,
    gst_tolerance: float = 0.05,
    precedence: list | None = None,
) -> List[Dict[str, Any]]:
    """
    Classify every invoice in the dataset.

    Args:
        invoices: vendor_invoices DataFrame.
        purchase_orders: purchase_orders DataFrame.
        vendors: vendors DataFrame.
        rate_tolerance: Absolute tolerance for rate comparison.
        gst_tolerance: Absolute tolerance for GST comparison.
        precedence: Optional custom precedence order.

    Returns:
        List of classification result dicts, one per invoice.
    """
    po_lookup = _build_po_lookup(purchase_orders)
    vendor_lookup = _build_vendor_lookup(vendors)
    po_invoice_groups = _build_po_invoice_groups(invoices)

    results = []
    for _, row in invoices.iterrows():
        result = classify_invoice(
            inv_row=row.to_dict(),
            po_lookup=po_lookup,
            vendor_lookup=vendor_lookup,
            po_invoice_groups=po_invoice_groups,
            rate_tolerance=rate_tolerance,
            gst_tolerance=gst_tolerance,
            precedence=precedence,
        )
        results.append(result)

    return results


def results_to_submission(results: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert classification results to the submission DataFrame format."""
    rows = [{"invoice_number": r["invoice_number"], "status": r["status"]} for r in results]
    df = pd.DataFrame(rows)

    # Validate output
    assert set(df["status"].unique()).issubset(VALID_STATUSES), \
        f"Unexpected statuses: {set(df['status'].unique()) - VALID_STATUSES}"

    return df

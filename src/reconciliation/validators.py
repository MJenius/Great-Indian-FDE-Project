"""
validators.py — Independent validators for each reconciliation check.

Each validator is a pure function that returns a structured ValidationResult.
Validators do NOT make classification decisions — they produce evidence
that the classifier/resolver consumes.

Design:
  - Every validator returns a dict with at minimum: {"passed": bool, "reason": str}
  - Additional diagnostic fields are included for auditability.
  - Validators are independent — they do not call each other.
  - Tolerance thresholds are explicit parameters, not hidden constants.
"""
from __future__ import annotations

from typing import Any, Dict

from .normalization import NormalizedUOM, convert_to_base_unit, normalize_uom

# Type alias for structured validation results
ValidationResult = Dict[str, Any]


# ---------- PO existence ----------

def validate_po_exists(po_number: str, po_lookup: dict) -> ValidationResult:
    """
    Check whether the invoice's PO reference exists in the PO master.

    Args:
        po_number: The po_number from the invoice.
        po_lookup: Dict mapping po_number -> PO row (or set of known PO numbers).

    Returns:
        ValidationResult with passed=True if PO exists.
    """
    exists = po_number in po_lookup
    return {
        "check": "po_exists",
        "passed": exists,
        "reason": "PO exists in master" if exists else f"PO '{po_number}' not found in purchase order master",
        "po_number": po_number,
    }


# ---------- Vendor identity ----------

def validate_vendor(
    invoice_vendor_id: str,
    po_vendor_id: str,
    vendor_master: dict | None = None,
) -> ValidationResult:
    """
    Check whether the invoice vendor_id matches the PO vendor_id.

    The match is strictly on vendor_id (the contractual key).
    GSTIN/name similarity is recorded for diagnostics but does NOT
    override a vendor_id mismatch.

    Args:
        invoice_vendor_id: vendor_id on the invoice.
        po_vendor_id: vendor_id on the matched PO.
        vendor_master: Optional dict mapping vendor_id -> vendor record for diagnostics.
    """
    match = invoice_vendor_id == po_vendor_id
    result: ValidationResult = {
        "check": "vendor",
        "passed": match,
        "reason": "Vendor IDs match" if match else "Vendor ID on invoice differs from PO",
        "invoice_vendor_id": invoice_vendor_id,
        "po_vendor_id": po_vendor_id,
    }

    # Diagnostic enrichment: if both exist in master, note GSTIN relationship
    if not match and vendor_master:
        inv_rec = vendor_master.get(invoice_vendor_id, {})
        po_rec = vendor_master.get(po_vendor_id, {})
        inv_gstin = inv_rec.get("gstin", "")
        po_gstin = po_rec.get("gstin", "")
        result["invoice_gstin"] = inv_gstin
        result["po_gstin"] = po_gstin
        result["same_gstin"] = inv_gstin == po_gstin and inv_gstin != ""
        result["invoice_vendor_name"] = inv_rec.get("vendor_name", "")
        result["po_vendor_name"] = po_rec.get("vendor_name", "")

    return result


# ---------- UOM ----------

def validate_uom(invoice_uom: str, po_uom: str) -> ValidationResult:
    """
    Check whether the invoice UOM matches the PO UOM.

    Also parses both UOMs to identify the conversion factor, which downstream
    validators can use to determine whether qty/rate differences are explained
    by the UOM difference.

    Args:
        invoice_uom: UOM string from the invoice.
        po_uom: UOM string from the PO.
    """
    inv_norm = normalize_uom(invoice_uom)
    po_norm = normalize_uom(po_uom)

    raw_match = str(invoice_uom).strip() == str(po_uom).strip()
    base_match = inv_norm.base_unit == po_norm.base_unit

    return {
        "check": "uom",
        "passed": raw_match,
        "reason": "UOM matches" if raw_match else f"UOM mismatch: invoice='{invoice_uom}', PO='{po_uom}'",
        "invoice_uom_raw": invoice_uom,
        "po_uom_raw": po_uom,
        "invoice_uom_base": inv_norm.base_unit,
        "po_uom_base": po_norm.base_unit,
        "invoice_conversion_factor": inv_norm.conversion_factor,
        "po_conversion_factor": po_norm.conversion_factor,
        "base_units_compatible": base_match,
        "effective_factor": inv_norm.conversion_factor / po_norm.conversion_factor if po_norm.conversion_factor else None,
    }


# ---------- Quantity ----------

def validate_quantity(
    invoice_qty: float,
    po_qty: float,
    uom_result: ValidationResult | None = None,
) -> ValidationResult:
    """
    Check whether the invoice quantity matches the PO quantity.

    If a UOM validation result is provided and the UOM differs, this validator
    also checks whether the quantity difference is fully explained by the UOM
    conversion factor (e.g., 20 Box(10) = 200 Nos).

    Args:
        invoice_qty: Quantity on the invoice.
        po_qty: Quantity on the PO.
        uom_result: Optional result from validate_uom() for UOM-aware comparison.
    """
    match = invoice_qty == po_qty

    result: ValidationResult = {
        "check": "quantity",
        "passed": match,
        "reason": "Quantities match" if match else f"Quantity mismatch: invoice={invoice_qty}, PO={po_qty}",
        "invoice_qty": invoice_qty,
        "po_qty": po_qty,
        "difference": invoice_qty - po_qty,
    }

    # If UOM differs, check if the discrepancy is explained by the conversion factor
    if uom_result and not uom_result["passed"] and uom_result.get("effective_factor"):
        factor = uom_result["effective_factor"]
        # invoice_qty * factor should equal po_qty if difference is UOM-explained
        converted_qty = invoice_qty * factor
        explained = abs(converted_qty - po_qty) < 0.01
        result["uom_converted_qty"] = converted_qty
        result["explained_by_uom"] = explained

    return result


from decimal import Decimal, ROUND_HALF_UP

# ---------- Rate ----------

def validate_rate(
    invoice_rate: float,
    po_rate: float,
    tolerance: float = 0.01,
    uom_result: ValidationResult | None = None,
) -> ValidationResult:
    """
    Check whether the invoice rate matches the PO rate within tolerance using Decimal precision.
    """
    d_inv_rate = Decimal(str(invoice_rate))
    d_po_rate = Decimal(str(po_rate))
    d_tol = Decimal(str(tolerance))
    
    diff = abs(d_inv_rate - d_po_rate)
    match = diff <= d_tol

    result: ValidationResult = {
        "check": "rate",
        "passed": match,
        "reason": "Rates match" if match else f"Rate mismatch: invoice={invoice_rate}, PO={po_rate}, diff={float(diff):.2f}",
        "invoice_rate": invoice_rate,
        "po_rate": po_rate,
        "difference": float(diff),
        "tolerance": tolerance,
    }

    # If UOM differs, check if the discrepancy is explained by the conversion factor
    if uom_result and not uom_result["passed"] and uom_result.get("effective_factor"):
        d_factor = Decimal(str(uom_result["effective_factor"]))
        converted_rate = d_inv_rate / d_factor
        explained = abs(converted_rate - d_po_rate) <= d_tol
        result["uom_converted_rate"] = float(converted_rate)
        result["explained_by_uom"] = explained

    return result


# ---------- GST ----------

def validate_gst(
    taxable_value: float,
    gst_rate_pct: float,
    gst_amount: float,
    tolerance: float = 0.05,
) -> ValidationResult:
    """
    Check whether the GST amount matches taxable_value * gst_rate_pct / 100 with Decimal rounding.
    """
    d_taxable = Decimal(str(taxable_value))
    d_rate = Decimal(str(gst_rate_pct))
    d_gst_amt = Decimal(str(gst_amount))
    d_tol = Decimal(str(tolerance))

    # Standard two-decimal rounding (half up)
    d_expected = (d_taxable * d_rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    diff = abs(d_gst_amt - d_expected)
    match = diff <= d_tol

    return {
        "check": "gst",
        "passed": match,
        "reason": "GST amount is correct" if match else f"GST mismatch: invoice={gst_amount}, expected={float(d_expected)}, diff={float(diff):.2f}",
        "gst_amount": gst_amount,
        "expected_gst": float(d_expected),
        "difference": float(diff),
        "tolerance": tolerance,
        "taxable_value": taxable_value,
        "gst_rate_pct": gst_rate_pct,
    }


# ---------- Duplicate billing ----------

def validate_duplicate(
    invoice_number: str,
    invoice_date: str,
    po_number: str,
    all_invoices_for_po: list[dict],
) -> ValidationResult:
    """
    Check whether this invoice is a duplicate billing against the same PO.

    Rule: If multiple invoices reference the same PO, the one with the
    earliest invoice_date survives. All subsequent ones are duplicates.
    If dates are identical, the one appearing first in the dataset (by
    original row order / lexicographic invoice_number) survives.

    Args:
        invoice_number: This invoice's number.
        invoice_date: This invoice's date.
        po_number: The PO this invoice references.
        all_invoices_for_po: List of dicts with keys "invoice_number" and
            "invoice_date" for ALL invoices referencing this PO.
    """
    if len(all_invoices_for_po) <= 1:
        return {
            "check": "duplicate",
            "passed": True,
            "reason": "Only one invoice for this PO",
            "po_number": po_number,
            "invoice_count": 1,
            "is_duplicate": False,
        }

    # Sort by date, then by invoice_number for deterministic tiebreaker
    sorted_invoices = sorted(all_invoices_for_po, key=lambda x: (x["invoice_date"], x["invoice_number"]))
    surviving = sorted_invoices[0]

    is_dup = invoice_number != surviving["invoice_number"]

    return {
        "check": "duplicate",
        "passed": not is_dup,
        "reason": "Duplicate invoice" if is_dup else "Earliest invoice for this PO (survives)",
        "po_number": po_number,
        "invoice_count": len(all_invoices_for_po),
        "is_duplicate": is_dup,
        "surviving_invoice": surviving["invoice_number"],
        "surviving_date": surviving["invoice_date"],
        "this_invoice": invoice_number,
        "this_date": invoice_date,
    }

"""
resolver.py — Precedence resolution for multi-flag invoice rows.

When multiple validators fail for a single invoice, the resolver determines
the single final classification using an explicit, configurable precedence order.

Precedence design rationale (documented here as the single source of truth):

1. MISSING_PO — If the PO doesn't exist, no other checks are meaningful.
   All other validators require a matched PO row to compare against.

2. VENDOR_MISMATCH — If the vendor on the invoice is wrong, the entire
   invoice may be addressed to the wrong supplier. Quantity/rate/UOM
   comparisons against the wrong vendor's PO are unreliable.

3. UOM_MISMATCH — A UOM difference (e.g., Box(10) vs Nos) systematically
   causes the invoice qty and rate to appear different from the PO.
   Classifying as QTY or RATE when the root cause is UOM is incorrect
   and hurts macro-F1 by inflating those classes.

4. QTY_MISMATCH — After UOM is resolved, genuine quantity differences
   are the next priority (higher financial impact than rate differences
   because qty changes affect total value linearly).

5. RATE_MISMATCH — Price discrepancies that aren't explained by UOM.

6. GST_ERROR — Pure arithmetic check on the invoice's own fields.
   Only flagged when no other structural issue exists, because GST
   miscalculation on a structurally-wrong invoice is secondary.

7. DUPLICATE_INVOICE — Explicitly configurable precedence. In the public dataset,
   all 5 duplicate invoices are otherwise clean. Placing DUPLICATE_INVOICE after
   structural/arithmetic errors is an inferred domain rule: an invoice with a severe
   vendor or calculation defect is primarily identified by that defect before billing duplication.

8. CLEAN — Default if everything passes.
"""
from __future__ import annotations

from typing import Dict, List, Any

from .validators import ValidationResult

# The default precedence order (highest priority first).
# This is the order in which flags are checked. The first failing check wins.
DEFAULT_PRECEDENCE = [
    "MISSING_PO",
    "VENDOR_MISMATCH",
    "UOM_MISMATCH",
    "QTY_MISMATCH",
    "RATE_MISMATCH",
    "GST_ERROR",
    "DUPLICATE_INVOICE",
]


def resolve_classification(
    validation_results: Dict[str, ValidationResult],
    precedence: List[str] | None = None,
) -> dict:
    """
    Given validation results for a single invoice, determine the final classification.

    Args:
        validation_results: Dict mapping check name to its ValidationResult.
            Expected keys: "po_exists", "vendor", "uom", "quantity", "rate", "gst", "duplicate"
        precedence: Optional custom precedence order. Defaults to DEFAULT_PRECEDENCE.

    Returns:
        Dict with:
            - "status": The final classification string.
            - "reason": Why this classification was chosen.
            - "raw_flags": Dict of all flags that failed.
            - "precedence_used": The precedence list that was applied.
    """
    if precedence is None:
        precedence = DEFAULT_PRECEDENCE

    # Map check names to status labels
    CHECK_TO_STATUS = {
        "MISSING_PO": "po_exists",
        "VENDOR_MISMATCH": "vendor",
        "UOM_MISMATCH": "uom",
        "QTY_MISMATCH": "quantity",
        "RATE_MISMATCH": "rate",
        "GST_ERROR": "gst",
        "DUPLICATE_INVOICE": "duplicate",
    }

    # Collect all raw flag failures
    raw_flags: Dict[str, bool] = {}
    for status_label, check_key in CHECK_TO_STATUS.items():
        result = validation_results.get(check_key)
        if result is not None:
            raw_flags[status_label] = not result["passed"]
        else:
            raw_flags[status_label] = False

    # Special handling for QTY and RATE when UOM is the root cause:
    # If UOM mismatch exists and qty/rate differences are explained by the
    # UOM conversion factor, suppress QTY_MISMATCH and RATE_MISMATCH.
    if raw_flags.get("UOM_MISMATCH"):
        qty_result = validation_results.get("quantity", {})
        rate_result = validation_results.get("rate", {})
        if qty_result.get("explained_by_uom", False):
            raw_flags["QTY_MISMATCH"] = False
        if rate_result.get("explained_by_uom", False):
            raw_flags["RATE_MISMATCH"] = False

    # Apply precedence: first failing check wins
    for status_label in precedence:
        if raw_flags.get(status_label, False):
            check_key = CHECK_TO_STATUS[status_label]
            check_result = validation_results.get(check_key, {})
            return {
                "status": status_label,
                "reason": check_result.get("reason", f"Failed {status_label} check"),
                "raw_flags": raw_flags,
                "precedence_used": precedence,
            }

    return {
        "status": "CLEAN",
        "reason": "All checks passed",
        "raw_flags": raw_flags,
        "precedence_used": precedence,
    }

"""
test_validators.py — Unit tests for every individual validator.

Tests cover:
  - Happy paths (all checks pass)
  - Each known public edge case
  - Boundary/tolerance cases
  - UOM conversion logic
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.reconciliation.validators import (
    validate_po_exists,
    validate_vendor,
    validate_uom,
    validate_quantity,
    validate_rate,
    validate_gst,
    validate_duplicate,
)


# ============================================================
# PO existence
# ============================================================

class TestValidatePOExists:
    def test_existing_po(self):
        result = validate_po_exists("PO/2026/1234", {"PO/2026/1234": {}})
        assert result["passed"] is True

    def test_missing_po(self):
        result = validate_po_exists("PO/2026/9999", {"PO/2026/1234": {}})
        assert result["passed"] is False
        assert "not found" in result["reason"]

    def test_empty_lookup(self):
        result = validate_po_exists("PO/2026/1234", {})
        assert result["passed"] is False


# ============================================================
# Vendor identity
# ============================================================

class TestValidateVendor:
    def test_matching_vendor_ids(self):
        result = validate_vendor("V-1001", "V-1001")
        assert result["passed"] is True

    def test_different_vendor_ids(self):
        result = validate_vendor("V-1060", "V-1001")
        assert result["passed"] is False

    def test_different_ids_same_gstin_still_fails(self):
        """Vendor match is on vendor_id, not GSTIN."""
        master = {
            "V-1056": {"gstin": "24LEBED64501ZJ", "vendor_name": "APEX TOOLS PVT. LTD."},
            "V-1042": {"gstin": "24LEBED64501ZJ", "vendor_name": "Apex Tools"},
        }
        result = validate_vendor("V-1056", "V-1042", vendor_master=master)
        assert result["passed"] is False
        assert result["same_gstin"] is True

    def test_different_ids_different_gstin(self):
        master = {
            "V-1057": {"gstin": "27NSTLD88171ZJ", "vendor_name": "JYOTI CASTINGS PVT. LTD."},
            "V-1008": {"gstin": "29WMBGM07441ZB", "vendor_name": "Reliable Fasteners Pvt Ltd"},
        }
        result = validate_vendor("V-1057", "V-1008", vendor_master=master)
        assert result["passed"] is False
        assert result["same_gstin"] is False


# ============================================================
# UOM
# ============================================================

class TestValidateUOM:
    def test_matching_nos(self):
        result = validate_uom("Nos", "Nos")
        assert result["passed"] is True
        assert result["effective_factor"] == 1.0

    def test_box10_vs_nos(self):
        result = validate_uom("Box(10)", "Nos")
        assert result["passed"] is False
        assert result["invoice_conversion_factor"] == 10
        assert result["po_conversion_factor"] == 1
        assert result["effective_factor"] == 10.0
        assert result["base_units_compatible"] is True

    def test_nos_vs_box10(self):
        result = validate_uom("Nos", "Box(10)")
        assert result["passed"] is False
        assert result["effective_factor"] == 0.1

    def test_case_sensitivity(self):
        """UOM matching should be case-sensitive on raw value."""
        result = validate_uom("Nos", "Nos")
        assert result["passed"] is True

    def test_box_with_different_factor(self):
        result = validate_uom("Box(5)", "Nos")
        assert result["passed"] is False
        assert result["invoice_conversion_factor"] == 5
        assert result["effective_factor"] == 5.0

    def test_unknown_uom(self):
        result = validate_uom("Kg", "Nos")
        assert result["passed"] is False
        assert result["base_units_compatible"] is False


# ============================================================
# Quantity
# ============================================================

class TestValidateQuantity:
    def test_matching_quantities(self):
        result = validate_quantity(100, 100)
        assert result["passed"] is True

    def test_mismatched_quantities(self):
        result = validate_quantity(20, 30)
        assert result["passed"] is False
        assert result["difference"] == -10

    def test_uom_explained_quantity(self):
        """20 Box(10) = 200 Nos — qty mismatch is explained by UOM."""
        uom_result = {
            "passed": False,
            "effective_factor": 10.0,
        }
        result = validate_quantity(20, 200, uom_result=uom_result)
        assert result["passed"] is False  # raw qty still doesn't match
        assert result["explained_by_uom"] is True
        assert result["uom_converted_qty"] == 200.0

    def test_uom_not_fully_explaining_quantity(self):
        """UOM differs but quantities still don't match after conversion."""
        uom_result = {
            "passed": False,
            "effective_factor": 10.0,
        }
        result = validate_quantity(20, 150, uom_result=uom_result)
        assert result["passed"] is False
        assert result["explained_by_uom"] is False


# ============================================================
# Rate
# ============================================================

class TestValidateRate:
    def test_matching_rates(self):
        result = validate_rate(5781.65, 5781.65)
        assert result["passed"] is True

    def test_within_tolerance(self):
        # 0.005 diff is clearly within 0.01 tolerance
        result = validate_rate(5781.65, 5781.655, tolerance=0.01)
        assert result["passed"] is True

    def test_beyond_tolerance(self):
        result = validate_rate(5781.65, 5782.00, tolerance=0.01)
        assert result["passed"] is False

    def test_exactly_at_tolerance(self):
        # Use integer arithmetic to avoid float imprecision at exact boundary
        result = validate_rate(100.00, 100.005, tolerance=0.01)
        assert result["passed"] is True

    def test_just_beyond_tolerance(self):
        # 0.02 diff is clearly beyond 0.01 tolerance
        result = validate_rate(100.00, 100.02, tolerance=0.01)
        assert result["passed"] is False

    def test_uom_explained_rate(self):
        """57816.5 per Box(10) = 5781.65 per Nos."""
        uom_result = {
            "passed": False,
            "effective_factor": 10.0,
        }
        result = validate_rate(57816.5, 5781.65, tolerance=0.01, uom_result=uom_result)
        assert result["passed"] is False  # raw rates don't match
        assert result["explained_by_uom"] is True

    def test_uom_not_explaining_rate(self):
        uom_result = {
            "passed": False,
            "effective_factor": 10.0,
        }
        result = validate_rate(57816.5, 6000.00, tolerance=0.01, uom_result=uom_result)
        assert result["passed"] is False
        assert result["explained_by_uom"] is False


# ============================================================
# GST
# ============================================================

class TestValidateGST:
    def test_correct_gst(self):
        # 100000 * 18 / 100 = 18000.00
        result = validate_gst(100000.0, 18, 18000.00)
        assert result["passed"] is True

    def test_within_tolerance(self):
        result = validate_gst(100000.0, 18, 18000.04, tolerance=0.05)
        assert result["passed"] is True

    def test_exactly_at_tolerance(self):
        result = validate_gst(100000.0, 18, 18000.05, tolerance=0.05)
        assert result["passed"] is True

    def test_beyond_tolerance(self):
        result = validate_gst(100000.0, 18, 18000.06, tolerance=0.05)
        assert result["passed"] is False

    def test_large_gst_error(self):
        # e.g. SST00139: taxable=75196.68, expected=13535.40, actual=9023.60
        result = validate_gst(75196.68, 18, 9023.60, tolerance=0.05)
        assert result["passed"] is False
        assert result["difference"] > 4000

    def test_zero_taxable_value(self):
        result = validate_gst(0.0, 18, 0.0)
        assert result["passed"] is True

    def test_different_gst_rate(self):
        """If hidden tests use different GST rates."""
        result = validate_gst(100000.0, 12, 12000.00)
        assert result["passed"] is True


# ============================================================
# Duplicate
# ============================================================

class TestValidateDuplicate:
    def test_single_invoice_for_po(self):
        result = validate_duplicate(
            "INV-001", "2026-01-01", "PO-001",
            [{"invoice_number": "INV-001", "invoice_date": "2026-01-01"}],
        )
        assert result["passed"] is True
        assert result["is_duplicate"] is False

    def test_earlier_invoice_survives(self):
        all_for_po = [
            {"invoice_number": "INV-001", "invoice_date": "2026-01-01"},
            {"invoice_number": "INV-002", "invoice_date": "2026-02-01"},
        ]
        result1 = validate_duplicate("INV-001", "2026-01-01", "PO-001", all_for_po)
        assert result1["passed"] is True
        assert result1["is_duplicate"] is False

        result2 = validate_duplicate("INV-002", "2026-02-01", "PO-001", all_for_po)
        assert result2["passed"] is False
        assert result2["is_duplicate"] is True
        assert result2["surviving_invoice"] == "INV-001"

    def test_same_date_tiebreaker_by_invoice_number(self):
        """When dates are identical, lexicographic order of invoice_number breaks tie."""
        all_for_po = [
            {"invoice_number": "INV-002", "invoice_date": "2026-01-01"},
            {"invoice_number": "INV-001", "invoice_date": "2026-01-01"},
        ]
        result1 = validate_duplicate("INV-001", "2026-01-01", "PO-001", all_for_po)
        assert result1["passed"] is True  # INV-001 < INV-002 lexicographically

        result2 = validate_duplicate("INV-002", "2026-01-01", "PO-001", all_for_po)
        assert result2["passed"] is False

    def test_public_duplicate_nbp(self):
        """PO/2026/1538: NBP/2026/067 (2026-02-01) vs INV-NBP-0068 (2026-02-11)."""
        all_for_po = [
            {"invoice_number": "NBP/2026/067", "invoice_date": "2026-02-01"},
            {"invoice_number": "INV-NBP-0068", "invoice_date": "2026-02-11"},
        ]
        # NBP/2026/067 is earlier -> survives
        result_survivor = validate_duplicate("NBP/2026/067", "2026-02-01", "PO/2026/1538", all_for_po)
        assert result_survivor["is_duplicate"] is False

        result_dup = validate_duplicate("INV-NBP-0068", "2026-02-11", "PO/2026/1538", all_for_po)
        assert result_dup["is_duplicate"] is True

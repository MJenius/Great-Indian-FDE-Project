"""
test_normalization.py — Unit tests for normalization functions.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.reconciliation.normalization import (
    normalize_uom,
    normalize_vendor_name,
    normalize_po_reference,
    normalize_invoice_number,
    convert_to_base_unit,
)


class TestNormalizeUOM:
    def test_nos(self):
        result = normalize_uom("Nos")
        assert result.base_unit == "Nos"
        assert result.conversion_factor == 1
        assert result.is_base is True

    def test_box_10(self):
        result = normalize_uom("Box(10)")
        assert result.base_unit == "Nos"
        assert result.conversion_factor == 10
        assert result.is_base is False

    def test_box_5(self):
        result = normalize_uom("Box(5)")
        assert result.base_unit == "Nos"
        assert result.conversion_factor == 5

    def test_box_case_insensitive(self):
        result = normalize_uom("box(10)")
        assert result.base_unit == "Nos"
        assert result.conversion_factor == 10

    def test_whitespace_stripped(self):
        result = normalize_uom("  Nos  ")
        assert result.base_unit == "Nos"
        assert result.conversion_factor == 1

    def test_unknown_uom_passthrough(self):
        result = normalize_uom("Kg")
        assert result.base_unit == "Kg"
        assert result.conversion_factor == 1

    def test_empty_string(self):
        result = normalize_uom("")
        assert result.conversion_factor == 1


class TestConvertToBaseUnit:
    def test_box10_conversion(self):
        uom = normalize_uom("Box(10)")
        qty_base, rate_base = convert_to_base_unit(20, 57816.5, uom)
        assert qty_base == 200
        assert abs(rate_base - 5781.65) < 0.01

    def test_nos_no_conversion(self):
        uom = normalize_uom("Nos")
        qty_base, rate_base = convert_to_base_unit(100, 500.0, uom)
        assert qty_base == 100
        assert rate_base == 500.0


class TestNormalizeVendorName:
    def test_uppercase(self):
        assert normalize_vendor_name("apex tools") == "APEX TOOLS"

    def test_strip_pvt_ltd(self):
        assert normalize_vendor_name("APEX TOOLS PVT. LTD.") == "APEX TOOLS"

    def test_strip_private_limited(self):
        assert normalize_vendor_name("Jyoti Castings Private Limited") == "JYOTI CASTINGS"

    def test_strip_punctuation(self):
        # After stripping punctuation (&) and legal suffix (Co), only the core name remains
        assert normalize_vendor_name("Sharma Bearings & Co") == "SHARMA BEARINGS"

    def test_strip_whitespace(self):
        assert normalize_vendor_name("  Om Polymers  ") == "OM POLYMERS"


class TestNormalizePOReference:
    def test_passthrough(self):
        assert normalize_po_reference("PO/2026/1451") == "PO/2026/1451"

    def test_strip_whitespace(self):
        assert normalize_po_reference("  PO/2026/1451  ") == "PO/2026/1451"


class TestNormalizeInvoiceNumber:
    def test_passthrough(self):
        assert normalize_invoice_number("INV-KP&-0285") == "INV-KP&-0285"

    def test_strip_whitespace(self):
        assert normalize_invoice_number("  INV-001  ") == "INV-001"

"""
test_resolver.py — Tests for the precedence resolution logic.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.reconciliation.resolver import resolve_classification, DEFAULT_PRECEDENCE


def _make_result(passed: bool, check: str = "", **kwargs):
    return {"passed": passed, "check": check, "reason": f"{'pass' if passed else 'fail'} {check}", **kwargs}


class TestResolveClassification:

    def test_all_pass_is_clean(self):
        results = {
            "po_exists": _make_result(True),
            "vendor": _make_result(True),
            "uom": _make_result(True),
            "quantity": _make_result(True),
            "rate": _make_result(True),
            "gst": _make_result(True),
            "duplicate": _make_result(True),
        }
        out = resolve_classification(results)
        assert out["status"] == "CLEAN"

    def test_missing_po_wins_all(self):
        results = {
            "po_exists": _make_result(False),
        }
        out = resolve_classification(results)
        assert out["status"] == "MISSING_PO"

    def test_vendor_over_uom(self):
        results = {
            "po_exists": _make_result(True),
            "vendor": _make_result(False),
            "uom": _make_result(False),
            "quantity": _make_result(True),
            "rate": _make_result(True),
            "gst": _make_result(True),
            "duplicate": _make_result(True),
        }
        out = resolve_classification(results)
        assert out["status"] == "VENDOR_MISMATCH"

    def test_uom_over_qty_and_rate(self):
        """UOM mismatch with qty/rate explained by UOM -> UOM_MISMATCH, not QTY or RATE."""
        results = {
            "po_exists": _make_result(True),
            "vendor": _make_result(True),
            "uom": _make_result(False),
            "quantity": _make_result(False, explained_by_uom=True),
            "rate": _make_result(False, explained_by_uom=True),
            "gst": _make_result(True),
            "duplicate": _make_result(True),
        }
        out = resolve_classification(results)
        assert out["status"] == "UOM_MISMATCH"
        # QTY and RATE should be suppressed because they're explained by UOM
        assert out["raw_flags"]["QTY_MISMATCH"] is False
        assert out["raw_flags"]["RATE_MISMATCH"] is False

    def test_uom_plus_genuine_qty_mismatch(self):
        """UOM differs AND qty doesn't match even after conversion."""
        results = {
            "po_exists": _make_result(True),
            "vendor": _make_result(True),
            "uom": _make_result(False),
            "quantity": _make_result(False, explained_by_uom=False),
            "rate": _make_result(False, explained_by_uom=True),
            "gst": _make_result(True),
            "duplicate": _make_result(True),
        }
        out = resolve_classification(results)
        # UOM takes precedence because it comes first in the precedence list
        assert out["status"] == "UOM_MISMATCH"

    def test_qty_over_rate(self):
        results = {
            "po_exists": _make_result(True),
            "vendor": _make_result(True),
            "uom": _make_result(True),
            "quantity": _make_result(False),
            "rate": _make_result(False),
            "gst": _make_result(True),
            "duplicate": _make_result(True),
        }
        out = resolve_classification(results)
        assert out["status"] == "QTY_MISMATCH"

    def test_rate_over_gst(self):
        results = {
            "po_exists": _make_result(True),
            "vendor": _make_result(True),
            "uom": _make_result(True),
            "quantity": _make_result(True),
            "rate": _make_result(False),
            "gst": _make_result(False),
            "duplicate": _make_result(True),
        }
        out = resolve_classification(results)
        assert out["status"] == "RATE_MISMATCH"

    def test_gst_over_duplicate(self):
        results = {
            "po_exists": _make_result(True),
            "vendor": _make_result(True),
            "uom": _make_result(True),
            "quantity": _make_result(True),
            "rate": _make_result(True),
            "gst": _make_result(False),
            "duplicate": _make_result(False),
        }
        out = resolve_classification(results)
        assert out["status"] == "GST_ERROR"

    def test_duplicate_only(self):
        results = {
            "po_exists": _make_result(True),
            "vendor": _make_result(True),
            "uom": _make_result(True),
            "quantity": _make_result(True),
            "rate": _make_result(True),
            "gst": _make_result(True),
            "duplicate": _make_result(False),
        }
        out = resolve_classification(results)
        assert out["status"] == "DUPLICATE_INVOICE"

    def test_custom_precedence(self):
        """Verify that custom precedence order is respected."""
        results = {
            "po_exists": _make_result(True),
            "vendor": _make_result(False),
            "uom": _make_result(True),
            "quantity": _make_result(False),
            "rate": _make_result(True),
            "gst": _make_result(True),
            "duplicate": _make_result(True),
        }
        # Default: vendor > qty -> VENDOR_MISMATCH
        out1 = resolve_classification(results)
        assert out1["status"] == "VENDOR_MISMATCH"

        # Custom: qty before vendor
        custom = ["MISSING_PO", "QTY_MISMATCH", "VENDOR_MISMATCH", "UOM_MISMATCH",
                   "RATE_MISMATCH", "GST_ERROR", "DUPLICATE_INVOICE"]
        out2 = resolve_classification(results, precedence=custom)
        assert out2["status"] == "QTY_MISMATCH"

    def test_raw_flags_always_populated(self):
        results = {
            "po_exists": _make_result(True),
            "vendor": _make_result(True),
            "uom": _make_result(True),
            "quantity": _make_result(True),
            "rate": _make_result(True),
            "gst": _make_result(True),
            "duplicate": _make_result(True),
        }
        out = resolve_classification(results)
        assert "raw_flags" in out
        assert all(v is False for v in out["raw_flags"].values())

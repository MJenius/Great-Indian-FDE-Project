"""
test_public_dataset.py — Integration test against the full public dataset.

Verifies:
  1. All 250 invoices are classified.
  2. The class distribution matches the audited ground truth.
  3. Every known public edge case is correctly classified.
  4. Output format is valid.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.reconciliation.loader import load_datasets
from src.reconciliation.classifier import classify_all, results_to_submission, VALID_STATUSES


DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# Ground truth class distribution from the data audit (independently verified)
EXPECTED_DISTRIBUTION = {
    "CLEAN": 155,
    "QTY_MISMATCH": 21,
    "RATE_MISMATCH": 16,
    "GST_ERROR": 16,
    "UOM_MISMATCH": 13,
    "MISSING_PO": 12,
    "VENDOR_MISMATCH": 12,
    "DUPLICATE_INVOICE": 5,
}

# Known MISSING_PO invoices (PO references that don't exist in PO master)
KNOWN_MISSING_PO = [
    "INV-SP&-0294", "DPP/2026/230", "SH00063", "EF/2026/156",
    "INV-KP&-0284", "SP&/2026/292", "INV-OC-0165", "SB&/2026/080",
    "PFP/2026/108", "INV-SRP-0276", "HP00214", "KP00197",
]

# Known VENDOR_MISMATCH invoices
KNOWN_VENDOR_MISMATCH = [
    "INV-OPP-0083", "JCP00153", "ATP/2026/251", "INV-PFP-0109",
    "ATP00249", "INV-PFP-0107", "ATP00250", "INV-JCP-0155",
    "JCP00154", "JCP/2026/152", "INV-OPP-0082", "JCP/2026/156",
]

# Known UOM_MISMATCH invoices (Box(10) vs Nos)
KNOWN_UOM_MISMATCH = [
    "INV-TRP-0186", "INV-SRP-0277", "PST00116", "SH00061",
    "INV-HP-0210", "RST/2026/066", "PCP00153", "INV-JB&-0288",
    "SH/2026/054", "JEW/2026/155", "TRP00189", "INV-PP-0280",
    "INV-EF-0155",
]

# Known DUPLICATE_INVOICE invoices (the later invoice in each pair)
KNOWN_DUPLICATE = [
    "GEP00204",         # PO/2026/1451 (earlier: GEP/2026/203)
    "INV-SF&-0239",     # PO/2026/1516 (earlier: SF&00238)
    "INV-KP&-0286",     # PO/2026/1404 (earlier: INV-KP&-0285)
    "RFP00194",         # PO/2026/1533 (earlier: RFP00193)
    "INV-NBP-0068",     # PO/2026/1538 (earlier: NBP/2026/067)
]

# Known GST_ERROR invoices
KNOWN_GST_ERROR = [
    "SST00139", "INV-MEW-0186", "INV-MF&-0087", "RFP/2026/188",
    "SST00136", "OC00162", "INV-SRP-0274", "NP00069",
    "GS&00224", "MEW/2026/188", "SST00138", "OC00164",
    "SVB/2026/102", "JEW00157", "NBP/2026/065", "DPP/2026/233",
]


@pytest.fixture(scope="module")
def classification_results():
    """Run classification once for all tests in this module."""
    if not DATA_DIR.exists():
        pytest.skip("Data directory not found")
    load_result = load_datasets(DATA_DIR)
    results = classify_all(
        invoices=load_result.invoices,
        purchase_orders=load_result.purchase_orders,
        vendors=load_result.vendors,
    )
    return results, load_result


class TestOutputFormat:
    def test_row_count(self, classification_results):
        results, load_result = classification_results
        assert len(results) == 250

    def test_unique_invoice_numbers(self, classification_results):
        results, _ = classification_results
        inv_nums = [r["invoice_number"] for r in results]
        assert len(inv_nums) == len(set(inv_nums))

    def test_all_statuses_valid(self, classification_results):
        results, _ = classification_results
        for r in results:
            assert r["status"] in VALID_STATUSES, f"Invalid status '{r['status']}' for {r['invoice_number']}"

    def test_submission_format(self, classification_results):
        results, _ = classification_results
        submission = results_to_submission(results)
        assert list(submission.columns) == ["invoice_number", "status"]
        assert len(submission) == 250


class TestClassDistribution:
    def test_expected_distribution(self, classification_results):
        results, _ = classification_results
        actual = {}
        for r in results:
            actual[r["status"]] = actual.get(r["status"], 0) + 1

        for status, expected_count in EXPECTED_DISTRIBUTION.items():
            actual_count = actual.get(status, 0)
            assert actual_count == expected_count, \
                f"{status}: expected {expected_count}, got {actual_count}"


class TestKnownEdgeCases:
    def _get_status(self, results, invoice_number):
        for r in results:
            if r["invoice_number"] == invoice_number:
                return r["status"]
        raise ValueError(f"Invoice {invoice_number} not found in results")

    def test_missing_po_invoices(self, classification_results):
        results, _ = classification_results
        for inv in KNOWN_MISSING_PO:
            assert self._get_status(results, inv) == "MISSING_PO", \
                f"{inv} should be MISSING_PO"

    def test_vendor_mismatch_invoices(self, classification_results):
        results, _ = classification_results
        for inv in KNOWN_VENDOR_MISMATCH:
            assert self._get_status(results, inv) == "VENDOR_MISMATCH", \
                f"{inv} should be VENDOR_MISMATCH"

    def test_uom_mismatch_invoices(self, classification_results):
        results, _ = classification_results
        for inv in KNOWN_UOM_MISMATCH:
            assert self._get_status(results, inv) == "UOM_MISMATCH", \
                f"{inv} should be UOM_MISMATCH"

    def test_duplicate_invoices(self, classification_results):
        results, _ = classification_results
        for inv in KNOWN_DUPLICATE:
            assert self._get_status(results, inv) == "DUPLICATE_INVOICE", \
                f"{inv} should be DUPLICATE_INVOICE"

    def test_gst_error_invoices(self, classification_results):
        results, _ = classification_results
        for inv in KNOWN_GST_ERROR:
            assert self._get_status(results, inv) == "GST_ERROR", \
                f"{inv} should be GST_ERROR"

    def test_duplicate_survivors_are_clean(self, classification_results):
        """The earlier invoice in each duplicate pair should be CLEAN."""
        results, _ = classification_results
        survivors = ["GEP/2026/203", "SF&00238", "INV-KP&-0285", "RFP00193", "NBP/2026/067"]
        for inv in survivors:
            assert self._get_status(results, inv) == "CLEAN", \
                f"Survivor {inv} should be CLEAN"

    def test_uom_mismatch_not_classified_as_qty_or_rate(self, classification_results):
        """No UOM mismatch invoice should leak into QTY_MISMATCH or RATE_MISMATCH."""
        results, _ = classification_results
        for inv in KNOWN_UOM_MISMATCH:
            status = self._get_status(results, inv)
            assert status != "QTY_MISMATCH", \
                f"{inv} incorrectly classified as QTY_MISMATCH (should be UOM_MISMATCH)"
            assert status != "RATE_MISMATCH", \
                f"{inv} incorrectly classified as RATE_MISMATCH (should be UOM_MISMATCH)"

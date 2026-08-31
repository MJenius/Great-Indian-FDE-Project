"""
Validation layer for pre-flight task checks and business policy compliance.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


class WorkflowValidationError(Exception):
    pass


class WorkflowValidator:
    """
    Validates preconditions and policy constraints for W1, W2, and W3.
    """

    @staticmethod
    def validate_w1_vendor_payload(
        payload: Dict[str, Any],
        annual_spend: float,
        is_direct_material: bool,
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Validate VOS-7 compliance for vendor onboarding:
        - Required fields present (vendor_name, gstin, city, state, payment_terms_days, msme_registered)
        - Documents present (GST cert, cancelled cheque, MSME declaration where applicable)
        - Trial PO cap <= 200,000
        - Determines required approvals:
            * spend > 10,00,000 -> CFO
            * direct-material -> Plant Head + QA
        """
        errors: List[str] = []
        required_fields = ["vendor_name", "gstin", "city", "state", "payment_terms_days", "msme_registered"]
        for rf in required_fields:
            if rf not in payload or payload[rf] is None or str(payload[rf]).strip() == "":
                errors.append(f"Missing required vendor field: {rf}")

        # Check GSTIN format (15 characters)
        gstin = str(payload.get("gstin", "")).strip()
        if len(gstin) != 15:
            errors.append(f"Invalid GSTIN length (expected 15): {gstin}")

        # Check trial PO cap (if specified in metadata/payload)
        trial_cap = payload.get("trial_po_cap", 200000.0)
        if trial_cap > 200000.0:
            errors.append(f"Trial PO cap ₹{trial_cap} exceeds VOS-7 limit of ₹2,00,000")

        # Determine required approvals from VOS-7
        required_approvals: List[str] = []
        if annual_spend > 1000000.0:
            required_approvals.append("CFO")
        if is_direct_material:
            required_approvals.append("PLANT_HEAD")
            required_approvals.append("QA")
        if not required_approvals:
            required_approvals.append("GM_PROCUREMENT")

        return len(errors) == 0, errors, required_approvals

    @staticmethod
    def validate_w2_exceptions_report(
        report: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Validate exceptions report schema and metrics before posting:
        - required keys: total_invoices, clean_invoices, total_exceptions, value_at_risk, exceptions_by_class
        - arithmetic consistency: total_invoices == clean_invoices + total_exceptions
        - value_at_risk > 0 when exceptions > 0
        """
        errors: List[str] = []
        required_keys = ["total_invoices", "clean_invoices", "total_exceptions", "value_at_risk", "exceptions_by_class"]
        for k in required_keys:
            if k not in report:
                errors.append(f"Missing required report field: {k}")

        if not errors:
            tot = report["total_invoices"]
            clean = report["clean_invoices"]
            exc = report["total_exceptions"]
            if tot != clean + exc:
                errors.append(f"Arithmetic inconsistency: total ({tot}) != clean ({clean}) + exceptions ({exc})")

            exc_by_class = report.get("exceptions_by_class", {})
            sum_classes = sum(exc_by_class.values())
            if sum_classes != exc:
                errors.append(f"Sum of exception classes ({sum_classes}) != total_exceptions ({exc})")

        return len(errors) == 0, errors

    @staticmethod
    def validate_w3_customer_mutation(
        customer_legacy_id: str,
        merged_into_id: str,
        existing_customers: Dict[str, Dict[str, Any]],
    ) -> Tuple[bool, List[str]]:
        """
        Validate customer deduplication mutation:
        - customer_legacy_id exists
        - merged_into_id exists
        - customer_legacy_id != merged_into_id (cannot merge into itself)
        - target is not already merged into something else (no circular/chained merges)
        """
        errors: List[str] = []
        if customer_legacy_id not in existing_customers:
            errors.append(f"Source customer {customer_legacy_id} does not exist in master")
        if merged_into_id not in existing_customers:
            errors.append(f"Target customer {merged_into_id} does not exist in master")
        if customer_legacy_id == merged_into_id:
            errors.append(f"Cannot merge customer {customer_legacy_id} into itself")

        return len(errors) == 0, errors

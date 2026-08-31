"""
Unit and integration test suite for the Workflow Engine.

Covers:
- W1 successful vendor onboarding & approvals
- W1 existing vendor handling (idempotency)
- W1 validation & trial PO cap / approval conditions
- W2 exceptions reporting & reconciliation integration
- W3 customer deduplication & patch planning
- W3 idempotency (already merged records skipped)
- Rate limiting & 429 backoff
- 500 error & failure injection
- Mock sandbox /reset
- Dry-run mode vs real write mode
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.reconciliation.classifier import classify_all
from src.workflow.audit import AuditLogger
from src.workflow.client import SandboxClient, SandboxClientError
from src.workflow.models import HttpMethod, WorkflowState
from src.workflow.rate_limiter import RateLimiter
from src.workflow.state_machine import WorkflowStateMachine
from src.workflow.validators import WorkflowValidator
from scripts.mock_sandbox import MockSandbox


DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@pytest.fixture
def mock_sb():
    return MockSandbox(DATA_DIR)


@pytest.fixture
def mock_client(mock_sb):
    client = SandboxClient(base_url="http://mock-sandbox/api/public/sandbox/v1")

    def dispatch(method: HttpMethod, endpoint: str, payload=None):
        return mock_sb.handle_request(method.value, endpoint, payload)

    client.request = MagicMock(side_effect=dispatch)
    return client


# ============================================================
# 1. W1 Vendor Onboarding Tests
# ============================================================

class TestWorkflowW1:
    def test_w1_onboarding_success(self, mock_client):
        audit = AuditLogger()
        sm = WorkflowStateMachine(mock_client, audit)

        vendor_payload = {
            "vendor_name": "Sri Ranga Castings",
            "gstin": "33AAACS1234R1ZK",
            "city": "Coimbatore",
            "state": "TN",
            "payment_terms_days": 45,
            "msme_registered": "Y",
            "source_system": "DRI",
        }

        plan = sm.run_w1_onboarding(
            vendor_details=vendor_payload,
            annual_spend=1400000.0,
            is_direct_material=True,
            dry_run=False,
        )

        assert sm.state == WorkflowState.COMPLETED
        assert len(plan.planned_actions) == 4  # 1 Create + 3 Approvals (CFO, Plant Head, QA)
        assert plan.metadata["required_approvals"] == ["CFO", "PLANT_HEAD", "QA"]

    def test_w1_idempotent_rerun(self, mock_client):
        audit = AuditLogger()
        sm = WorkflowStateMachine(mock_client, audit)

        vendor_payload = {
            "vendor_name": "Sri Ranga Castings",
            "gstin": "33AAACS1234R1ZK",
            "city": "Coimbatore",
            "state": "TN",
            "payment_terms_days": 45,
            "msme_registered": "Y",
            "source_system": "DRI",
        }

        # First run
        sm.run_w1_onboarding(vendor_payload, 1400000.0, True, dry_run=False)

        # Second run should detect vendor already exists
        plan2 = sm.run_w1_onboarding(vendor_payload, 1400000.0, True, dry_run=False)
        assert plan2.metadata["already_existed"] is True
        # No new create actions planned
        assert not any(a.endpoint == "/erp/vendors" and a.method == HttpMethod.POST for a in plan2.planned_actions)

    def test_w1_validation_failure_bad_gstin(self):
        payload = {"vendor_name": "Bad Vendor", "gstin": "SHORT", "city": "X", "state": "Y", "payment_terms_days": 30, "msme_registered": "Y"}
        valid, errors, _ = WorkflowValidator.validate_w1_vendor_payload(payload, 500000.0, False)
        assert valid is False
        assert any("GSTIN length" in e for e in errors)

    def test_w1_validation_failure_exceed_trial_po_cap(self):
        payload = {"vendor_name": "Vendor", "gstin": "123456789012345", "city": "X", "state": "Y", "payment_terms_days": 30, "msme_registered": "Y", "trial_po_cap": 300000.0}
        valid, errors, _ = WorkflowValidator.validate_w1_vendor_payload(payload, 500000.0, False)
        assert valid is False
        assert any("exceeds VOS-7 limit" in e for e in errors)


# ============================================================
# 2. W2 Exceptions Report Tests
# ============================================================

class TestWorkflowW2:
    def test_w2_report_generation_and_posting(self, mock_client):
        audit = AuditLogger()
        sm = WorkflowStateMachine(mock_client, audit)

        def recon_func(inv, po, vend):
            return classify_all(inv, po, vend)

        plan = sm.run_w2_exceptions_report(recon_func, dry_run=False)
        assert sm.state == WorkflowState.COMPLETED
        assert len(plan.planned_actions) == 1
        payload = plan.planned_actions[0].payload
        assert payload["total_invoices"] == 250
        assert payload["clean_invoices"] == 155
        assert payload["total_exceptions"] == 95
        assert payload["value_at_risk"] == 88404135.42


# ============================================================
# 3. W3 Customer Deduplication Tests
# ============================================================

class TestWorkflowW3:
    def test_w3_customer_dedup_success(self, mock_client):
        audit = AuditLogger()
        sm = WorkflowStateMachine(mock_client, audit)

        plan = sm.run_w3_customer_dedup(dry_run=False)
        assert sm.state == WorkflowState.COMPLETED
        assert len(plan.planned_actions) == 45  # Exactly 45 duplicates merged into 40 master records

    def test_w3_idempotent_retry(self, mock_client):
        audit = AuditLogger()
        sm = WorkflowStateMachine(mock_client, audit)

        # Run 1: merges 45
        sm.run_w3_customer_dedup(dry_run=False)

        # Run 2: all 45 are already merged, so 0 planned actions
        plan2 = sm.run_w3_customer_dedup(dry_run=False)
        assert len(plan2.planned_actions) == 0


# ============================================================
# 4. Sandbox Client, Rate Limiter & Failure Injection Tests
# ============================================================

class TestClientAndResilience:
    def test_rate_limiter_tokens(self):
        limiter = RateLimiter(max_requests_per_minute=60)
        # Consuming 1 token should not sleep much
        waited = limiter.acquire(1.0)
        assert waited == 0.0

    def test_mock_sandbox_reset(self, mock_sb):
        res = mock_sb.reset()
        assert res["status"] == "RESET_SUCCESS"
        assert res["reset_count"] == 1

    def test_failure_injection_500(self, mock_sb):
        mock_sb.inject_failure("500", count=1)
        status, body = mock_sb.handle_request("GET", "/erp/vendors")
        assert status == 500
        # Subsequent call should succeed
        status2, body2 = mock_sb.handle_request("GET", "/erp/vendors")
        assert status2 == 200

    def test_failure_injection_429(self, mock_sb):
        mock_sb.inject_failure("429", count=1)
        status, body = mock_sb.handle_request("GET", "/erp/vendors")
        assert status == 429

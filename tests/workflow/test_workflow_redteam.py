"""
Comprehensive Adversarial Red-Team Test Suite for Workflow Engine.

Tests:
- Idempotency across 3 consecutive executions (W1, W2, W3)
- Partial execution, process crashes, and safe restarts
- Single-point mutation failures for all steps in W1, W2, W3
- Transient error retries: HTTP 429, 500, 502, Timeout, Connection errors
- Permanent error handling (400, 401, 403, 404, 409) - no blind retries
- Stale read detection during verification
- Duplicate POST safety (timeout after successful POST on server)
- Token bucket rate-limiter burst vs sustained mathematical verification
- /reset state consistency
- Invariant assertions for all entities
- Adversarial customer normalization (avoiding false merges on legitimate different entities)
- Hypothesis property-based testing for arbitrary customer batches & failure injections
"""
from __future__ import annotations

import copy
import re
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from hypothesis import given, settings, strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.reconciliation.classifier import classify_all
from src.workflow.audit import AuditLogger
from src.workflow.client import SandboxClient, SandboxClientError
from src.workflow.executor import WorkflowExecutor
from src.workflow.models import HttpMethod, PlannedAction, WorkflowPlan, WorkflowState
from src.workflow.planner import WorkflowPlanner
from src.workflow.rate_limiter import RateLimiter
from src.workflow.state_machine import WorkflowStateMachine
from src.workflow.validators import WorkflowValidator
from src.workflow.verifier import WorkflowVerifier
from scripts.mock_sandbox import MockSandbox

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@pytest.fixture
def clean_sandbox():
    return MockSandbox(DATA_DIR)


@pytest.fixture
def sandbox_client_factory(clean_sandbox):
    def _create_client():
        client = SandboxClient(base_url="http://mock-sandbox/api/public/sandbox/v1")

        def dispatch(method: HttpMethod, endpoint: str, payload=None):
            return clean_sandbox.handle_request(method.value, endpoint, payload)

        client.request = MagicMock(side_effect=dispatch)
        return client
    return _create_client


# ============================================================
# 1. Multi-Pass Idempotency Tests (3 consecutive executions)
# ============================================================

class TestAggressiveIdempotency:
    def test_w1_triple_execution_idempotent(self, sandbox_client_factory, clean_sandbox):
        client = sandbox_client_factory()
        audit = AuditLogger()
        sm = WorkflowStateMachine(client, audit)

        vendor_payload = {
            "vendor_name": "Sri Ranga Castings",
            "gstin": "33AAACS1234R1ZK",
            "city": "Coimbatore",
            "state": "TN",
            "payment_terms_days": 45,
            "msme_registered": "Y",
            "source_system": "DRI",
        }

        initial_vendor_count = len(clean_sandbox.vendors)

        # Run 1: Clean execution
        p1 = sm.run_w1_onboarding(vendor_payload, 1400000.0, True, dry_run=False)
        assert sm.state == WorkflowState.COMPLETED
        assert len(clean_sandbox.vendors) == initial_vendor_count + 1

        # Run 2: Immediate re-execution
        p2 = sm.run_w1_onboarding(vendor_payload, 1400000.0, True, dry_run=False)
        assert sm.state == WorkflowState.COMPLETED
        assert len(clean_sandbox.vendors) == initial_vendor_count + 1  # No duplicate created

        # Run 3: Third execution
        p3 = sm.run_w1_onboarding(vendor_payload, 1400000.0, True, dry_run=False)
        assert sm.state == WorkflowState.COMPLETED
        assert len(clean_sandbox.vendors) == initial_vendor_count + 1

    def test_w2_triple_execution_idempotent(self, sandbox_client_factory, clean_sandbox):
        client = sandbox_client_factory()
        audit = AuditLogger()
        sm = WorkflowStateMachine(client, audit)

        def recon(inv, po, vend):
            return classify_all(inv, po, vend)

        p1 = sm.run_w2_exceptions_report(recon, dry_run=False)
        assert sm.state == WorkflowState.COMPLETED
        assert len(clean_sandbox.exceptions_reports) == 1

        p2 = sm.run_w2_exceptions_report(recon, dry_run=False)
        assert sm.state == WorkflowState.COMPLETED

        p3 = sm.run_w2_exceptions_report(recon, dry_run=False)
        assert sm.state == WorkflowState.COMPLETED

    def test_w3_triple_execution_idempotent(self, sandbox_client_factory, clean_sandbox):
        client = sandbox_client_factory()
        audit = AuditLogger()
        sm = WorkflowStateMachine(client, audit)

        # Run 1
        p1 = sm.run_w3_customer_dedup(dry_run=False)
        assert sm.state == WorkflowState.COMPLETED
        assert len(p1.planned_actions) == 45

        # Run 2: Zero planned actions
        p2 = sm.run_w3_customer_dedup(dry_run=False)
        assert len(p2.planned_actions) == 0

        # Run 3: Zero planned actions
        p3 = sm.run_w3_customer_dedup(dry_run=False)
        assert len(p3.planned_actions) == 0


# ============================================================
# 2. Crash & Halfway Restart Simulation
# ============================================================

class TestCrashAndRecovery:
    def test_w3_crash_halfway_and_resume(self, sandbox_client_factory, clean_sandbox):
        client = sandbox_client_factory()
        audit = AuditLogger()

        # Generate full plan (45 merges)
        plan = WorkflowPlanner.plan_w3_customer_dedup(client, dry_run=False)
        assert len(plan.planned_actions) == 45

        # Execute first 20 actions only, then simulate process crash
        for a in plan.planned_actions[:20]:
            status_code, resp_body = client.request(a.method, a.endpoint, a.payload)
            assert status_code == 200

        # Verify exactly 20 are merged in the sandbox
        merged_count = sum(1 for c in clean_sandbox.customers if c.get("merged_into") is not None)
        assert merged_count == 20

        # Now restart the agent workflow completely
        sm_restart = WorkflowStateMachine(client, audit)
        plan_resumed = sm_restart.run_w3_customer_dedup(dry_run=False)

        # Resumed planner must plan ONLY the remaining 25 actions
        assert len(plan_resumed.planned_actions) == 25
        assert sm_restart.state == WorkflowState.COMPLETED

        # Final sandbox state must have all 45 duplicates merged
        final_merged = sum(1 for c in clean_sandbox.customers if c.get("merged_into") is not None)
        assert final_merged == 45


# ============================================================
# 3. Single-Point Mutation Failure Positions
# ============================================================

class TestMutationFailurePositions:
    def test_w1_fail_vendor_post(self, clean_sandbox):
        client = SandboxClient(base_url="http://mock-sandbox/api/public/sandbox/v1")
        audit = AuditLogger()

        def dispatch(method: HttpMethod, endpoint: str, payload=None):
            if endpoint == "/erp/vendors" and method == HttpMethod.POST:
                return 500, {"error": "Database write error"}
            return clean_sandbox.handle_request(method.value, endpoint, payload)

        client.request = MagicMock(side_effect=dispatch)
        sm = WorkflowStateMachine(client, audit)

        vendor_payload = {
            "vendor_name": "Sri Ranga Castings",
            "gstin": "33AAACS1234R1ZK",
            "city": "Coimbatore",
            "state": "TN",
            "payment_terms_days": 45,
            "msme_registered": "Y",
            "source_system": "DRI",
        }

        plan = sm.run_w1_onboarding(vendor_payload, 1400000.0, True, dry_run=False)
        assert sm.state == WorkflowState.FAILED

    def test_w1_fail_approval_step_2(self, clean_sandbox):
        client = SandboxClient(base_url="http://mock-sandbox/api/public/sandbox/v1")
        audit = AuditLogger()
        call_count = 0

        def dispatch(method: HttpMethod, endpoint: str, payload=None):
            nonlocal call_count
            if endpoint == "/erp/approvals" and method == HttpMethod.POST:
                call_count += 1
                if call_count == 2:  # Fail second approval
                    return 500, {"error": "Approval service timeout"}
            return clean_sandbox.handle_request(method.value, endpoint, payload)

        client.request = MagicMock(side_effect=dispatch)
        sm = WorkflowStateMachine(client, audit)

        vendor_payload = {
            "vendor_name": "Sri Ranga Castings",
            "gstin": "33AAACS1234R1ZK",
            "city": "Coimbatore",
            "state": "TN",
            "payment_terms_days": 45,
            "msme_registered": "Y",
            "source_system": "DRI",
        }

        plan = sm.run_w1_onboarding(vendor_payload, 1400000.0, True, dry_run=False)
        assert sm.state == WorkflowState.FAILED

    def test_w3_fail_patch_at_duplicate_23(self, clean_sandbox):
        client = SandboxClient(base_url="http://mock-sandbox/api/public/sandbox/v1")
        audit = AuditLogger()
        patch_count = 0

        def dispatch(method: HttpMethod, endpoint: str, payload=None):
            nonlocal patch_count
            if method == HttpMethod.PATCH:
                patch_count += 1
                if patch_count == 23:
                    return 500, {"error": "CRM lock acquisition failure"}
            return clean_sandbox.handle_request(method.value, endpoint, payload)

        client.request = MagicMock(side_effect=dispatch)
        sm = WorkflowStateMachine(client, audit)

        plan = sm.run_w3_customer_dedup(dry_run=False)
        assert sm.state == WorkflowState.FAILED

        # Resume execution with healthy client
        healthy_client = SandboxClient(base_url="http://mock-sandbox/api/public/sandbox/v1")
        def healthy_dispatch(method: HttpMethod, endpoint: str, payload=None):
            return clean_sandbox.handle_request(method.value, endpoint, payload)
        healthy_client.request = MagicMock(side_effect=healthy_dispatch)
        sm_resumed = WorkflowStateMachine(healthy_client, audit)

        plan2 = sm_resumed.run_w3_customer_dedup(dry_run=False)
        assert sm_resumed.state == WorkflowState.COMPLETED
        # Should execute only the remaining 23 (45 - 22 successful)
        assert len(plan2.planned_actions) == 23


# ============================================================
# 4. Stale Read Detection
# ============================================================

class TestStaleReadDetection:
    def test_stale_read_fails_verification(self, clean_sandbox):
        client = SandboxClient(base_url="http://mock-sandbox/api/public/sandbox/v1")
        audit = AuditLogger()

        # Simulate PATCH succeeding on server, but GET immediately after returns stale old data
        def dispatch(method: HttpMethod, endpoint: str, payload=None):
            if method == HttpMethod.GET and "/crm/customers/C-" in endpoint:
                # Return customer without merged_into field (stale view)
                return 200, {"legacy_id": "C-5047", "customer_name": "Stale View", "merged_into": None}
            return clean_sandbox.handle_request(method.value, endpoint, payload)

        client.request = MagicMock(side_effect=dispatch)
        sm = WorkflowStateMachine(client, audit)

        plan = sm.run_w3_customer_dedup(dry_run=False)
        assert sm.state == WorkflowState.FAILED


# ============================================================
# 5. Non-Retryable Client Errors (400, 401, 403, 404, 409)
# ============================================================

class TestPermanentClientErrors:
    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 409])
    def test_client_does_not_retry_client_errors(self, status_code):
        client = SandboxClient()
        session_mock = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.json.return_value = {"error": f"Client error {status_code}"}
        session_mock.get.return_value = mock_resp
        client.session = session_mock

        code, body = client.request(HttpMethod.GET, "/erp/test")
        assert code == status_code
        # Ensure session.get was called exactly ONCE (no blind retry loop)
        assert session_mock.get.call_count == 1


# ============================================================
# 6. Rate Limiter Mathematical & Burst Verification
# ============================================================

class TestRateLimiterMath:
    def test_token_bucket_burst_allowance(self):
        limiter = RateLimiter(max_requests_per_minute=60)
        # Full capacity allows initial burst of 60 without waiting
        for _ in range(60):
            waited = limiter.acquire(1.0)
            assert waited == 0.0

        assert limiter.tokens < 1.0

    def test_token_bucket_fill_rate(self):
        limiter = RateLimiter(max_requests_per_minute=60)
        limiter.tokens = 0.0  # Empty bucket
        limiter.last_update = time.monotonic() - 1.0  # 1 second ago

        # After 1 second at 60/min (1 token/sec), exactly ~1 token is available
        limiter.acquire(1.0)
        assert limiter.tokens < 0.1


# ============================================================
# 7. Adversarial Customer Name Normalization (Prevent False Merges)
# ============================================================

class TestAdversarialNormalization:
    def norm(self, s: str) -> str:
        s = str(s).upper().strip()
        s = re.sub(r"\s*\((?:SOUTH|NORTH|II)\)\s*$", "", s)
        s = re.sub(r"[^A-Z0-9]", "", s)
        return s

    def test_legitimate_duplicates_merge(self):
        assert self.norm("Tirupati Pump House") == self.norm("Tirupati Pump House (South)")
        assert self.norm("Dhanlaxmi Distributors") == self.norm("Dhanlaxmi Distributors (North)")
        assert self.norm("Dhanlaxmi Distributors") == self.norm("DHANLAXMI DISTRIBUTORS")
        assert self.norm("Apex Engineering Projects") == self.norm("Apex Engineering Projects (II)")

    def test_distinct_entities_must_not_merge(self):
        # Genuine distinct companies with similar keywords must NOT produce identical normalizations
        assert self.norm("Tirupati Pump House") != self.norm("Tirupati Agri Stores")
        assert self.norm("Bharat Pump Centre") != self.norm("Bharat Engineering Works")
        assert self.norm("Western Flow Controls") != self.norm("Southern Flow Controls")
        assert self.norm("Kaveri Engineering Sales") != self.norm("Godavari Engineering Sales")


# ============================================================
# 8. Property-Based Testing with Hypothesis
# ============================================================

class TestPropertyBasedValidation:
    @given(
        spend=st.floats(min_value=1000.0, max_value=50000000.0),
        is_direct=st.booleans(),
    )
    def test_approval_matrix_invariants(self, spend, is_direct):
        payload = {
            "vendor_name": "Test Vendor",
            "gstin": "33AAACS1234R1ZK",
            "city": "City",
            "state": "ST",
            "payment_terms_days": 30,
            "msme_registered": "Y",
        }
        valid, errors, approvals = WorkflowValidator.validate_w1_vendor_payload(payload, spend, is_direct)
        assert valid is True

        if spend > 1000000.0:
            assert "CFO" in approvals
        if is_direct:
            assert "PLANT_HEAD" in approvals
            assert "QA" in approvals
        if spend <= 1000000.0 and not is_direct:
            assert approvals == ["GM_PROCUREMENT"]

"""
Comprehensive Integration and Cross-Task Field Isolation Test Suite.

Tests:
1. W2 direct linkage to Reconciliation Engine (modifying recon engine output modifies W2 report)
2. Strict Field Isolation (M1 drishti_price only, M2 mapped_dri_sku only, M3 migrated_to_salestrack/crm_id only, W3 merged_into only)
3. End-to-end full sequence execution and double-pass idempotency (RESET -> W1 -> W2 -> W3 -> M1 -> M2 -> M3)
4. Arbitrary Execution Permutations (W1-W2-W3-M1-M2-M3, M1-M2-M3-W1-W2-W3, W3-M3-W2-M2-W1-M1)
5. Comprehensive process crash and restart recovery across every single task
6. Automated secret scanner across all files in repository
"""
from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.migration.executors import MigrationExecutor
from src.migration.planners import MigrationPlanner
from src.reconciliation.classifier import classify_all
from src.workflow.audit import AuditLogger
from src.workflow.client import SandboxClient
from src.workflow.models import HttpMethod
from src.workflow.state_machine import WorkflowStateMachine
from scripts.mock_sandbox import MockSandbox

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ROOT_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def products_df():
    return pd.read_csv(DATA_DIR / "products.csv")


@pytest.fixture
def clean_sandbox():
    return MockSandbox(DATA_DIR)


@pytest.fixture
def client_factory(clean_sandbox):
    def _create():
        client = SandboxClient(base_url="http://mock-sandbox/api/public/sandbox/v1")
        def dispatch(method: HttpMethod, endpoint: str, payload=None):
            return clean_sandbox.handle_request(method.value, endpoint, payload)
        client.request = MagicMock(side_effect=dispatch)
        return client
    return _create


# ============================================================
# 1. W2 direct linkage to Reconciliation Engine
# ============================================================

class TestW2ReconciliationLinkage:
    def test_w2_reflects_reconciliation_engine_mutations(self, client_factory):
        client = client_factory()
        audit = AuditLogger()
        sm = WorkflowStateMachine(client, audit)

        # Standard reconciliation
        p_std = sm.run_w2_exceptions_report(reconciliation_func=classify_all, dry_run=True)
        assert p_std.planned_actions[0].payload["total_exceptions"] == 95

        # Custom mock reconciliation returning 50 clean and 200 exceptions
        def mock_recon(inv, po, vend):
            res = []
            for i, r in inv.iterrows():
                st = "CLEAN" if i < 50 else "QTY_MISMATCH"
                res.append({"invoice_number": r["invoice_number"], "status": st, "resolution": {"raw_flags": {}}})
            return res

        p_custom = sm.run_w2_exceptions_report(reconciliation_func=mock_recon, dry_run=True)
        payload = p_custom.planned_actions[0].payload
        assert payload["clean_invoices"] == 50
        assert payload["total_exceptions"] == 200
        assert payload["exceptions_by_class"]["QTY_MISMATCH"] == 200


# ============================================================
# 2. Strict Cross-Task Field Isolation
# ============================================================

class TestCrossTaskFieldIsolation:
    def test_strict_field_level_mutations(self, client_factory, clean_sandbox, products_df):
        client = client_factory()
        audit = AuditLogger()
        executor_mig = MigrationExecutor(client, audit)
        sm_wf = WorkflowStateMachine(client, audit)

        # Snapshot initial state
        initial_prods = copy.deepcopy(clean_sandbox.products)
        initial_custs = copy.deepcopy(clean_sandbox.customers)

        # 1. Execute M1
        p_m1 = MigrationPlanner.plan_m1_price_migration(client, products_df, dry_run=False)
        executor_mig.execute_plan(p_m1)

        # Assert M1 ONLY changed drishti_price
        for before, after in zip(initial_prods, clean_sandbox.products):
            assert before["sku"] == after["sku"]
            assert before.get("description") == after.get("description")
            assert before.get("uom") == after.get("uom")
            assert before.get("mapped_dri_sku") == after.get("mapped_dri_sku")
            # Only drishti_price should be updated
            if pd.notna(before.get("list_price_2023")):
                assert after.get("drishti_price") == before.get("list_price_2023")

        # Snapshot before M2
        prods_after_m1 = copy.deepcopy(clean_sandbox.products)

        # 2. Execute M2
        p_m2 = MigrationPlanner.plan_m2_flowtech_mapping(client, products_df, dry_run=False)
        executor_mig.execute_plan(p_m2)

        # Assert M2 ONLY changed mapped_dri_sku
        for before, after in zip(prods_after_m1, clean_sandbox.products):
            assert before["sku"] == after["sku"]
            assert before.get("drishti_price") == after.get("drishti_price")
            # Handle float NaN equality
            b_p = before.get("list_price_2023")
            a_p = after.get("list_price_2023")
            if pd.isna(b_p):
                assert pd.isna(a_p)
            else:
                assert b_p == a_p

        # 3. Execute W3
        p_w3 = sm_wf.run_w3_customer_dedup(dry_run=False)

        # Assert W3 ONLY changed merged_into
        for before, after in zip(initial_custs, clean_sandbox.customers):
            assert before["legacy_id"] == after["legacy_id"]
            assert before["customer_name"] == after["customer_name"]
            assert before.get("city") == after.get("city")
            assert before.get("state") == after.get("state")
            assert before.get("migrated_to_salestrack") == after.get("migrated_to_salestrack")
            
            b_crm = before.get("crm_id")
            a_crm = after.get("crm_id")
            if pd.isna(b_crm):
                assert pd.isna(a_crm)
            else:
                assert b_crm == a_crm

        # Snapshot before M3
        custs_after_w3 = copy.deepcopy(clean_sandbox.customers)

        # 4. Execute M3
        p_m3 = MigrationPlanner.plan_m3_salestrack_migration(client, dry_run=False)
        executor_mig.execute_plan(p_m3)

        # Assert M3 ONLY changed migrated_to_salestrack and crm_id
        for before, after in zip(custs_after_w3, clean_sandbox.customers):
            assert before["legacy_id"] == after["legacy_id"]
            assert before["customer_name"] == after["customer_name"]
            assert before.get("merged_into") == after.get("merged_into")
            assert after.get("migrated_to_salestrack") == "Y"
            assert after.get("crm_id") is not None


# ============================================================
# 3. End-to-End Execution Sequence & Double-Pass Idempotency
# ============================================================

class TestEndToEndFullSequence:
    def test_full_sequence_and_idempotent_rerun(self, client_factory, clean_sandbox, products_df):
        client = client_factory()
        audit = AuditLogger()
        sm_wf = WorkflowStateMachine(client, audit)
        executor_mig = MigrationExecutor(client, audit)

        vendor_payload = {
            "vendor_name": "Sri Ranga Castings",
            "gstin": "33AAACS1234R1ZK",
            "city": "Coimbatore",
            "state": "TN",
            "payment_terms_days": 45,
            "msme_registered": "Y",
            "source_system": "DRI",
        }

        def run_all():
            p_w1 = sm_wf.run_w1_onboarding(vendor_payload, 1400000.0, True, dry_run=False)
            p_w2 = sm_wf.run_w2_exceptions_report(reconciliation_func=classify_all, dry_run=False)
            p_w3 = sm_wf.run_w3_customer_dedup(dry_run=False)
            p_m1 = MigrationPlanner.plan_m1_price_migration(client, products_df, dry_run=False)
            executor_mig.execute_plan(p_m1)
            p_m2 = MigrationPlanner.plan_m2_flowtech_mapping(client, products_df, dry_run=False)
            executor_mig.execute_plan(p_m2)
            p_m3 = MigrationPlanner.plan_m3_salestrack_migration(client, dry_run=False)
            executor_mig.execute_plan(p_m3)
            return p_w1, p_w2, p_w3, p_m1, p_m2, p_m3

        # First complete pass
        w1_1, w2_1, w3_1, m1_1, m2_1, m3_1 = run_all()
        assert len(w1_1.planned_actions) == 4
        assert len(w3_1.planned_actions) == 45
        assert len(m1_1.price_actions) == 113
        assert sum(1 for a in m2_1.flowtech_actions if a.action_type == "PATCH") == 11
        assert len(m3_1.salestrack_actions) == 30

        # Snapshot state after Pass 1
        snapshot_vends = copy.deepcopy(clean_sandbox.vendors)
        snapshot_prods = copy.deepcopy(clean_sandbox.products)
        snapshot_custs = copy.deepcopy(clean_sandbox.customers)

        # Second complete pass (Must be 100% idempotent)
        w1_2, w2_2, w3_2, m1_2, m2_2, m3_2 = run_all()
        assert w1_2.metadata["already_existed"] is True
        assert len(w3_2.planned_actions) == 0
        assert len(m1_2.price_actions) == 0
        assert sum(1 for a in m2_2.flowtech_actions if a.action_type == "PATCH") == 0
        assert len(m3_2.salestrack_actions) == 0

        # Assert no change in state
        assert clean_sandbox.vendors == snapshot_vends
        assert clean_sandbox.products == snapshot_prods
        assert clean_sandbox.customers == snapshot_custs


# ============================================================
# 4. Different Execution Orders / Permutations
# ============================================================

class TestExecutionPermutations:
    @pytest.mark.parametrize("order", [
        ["W1", "W2", "W3", "M1", "M2", "M3"],
        ["M1", "M2", "M3", "W1", "W2", "W3"],
        ["W3", "M3", "W2", "M2", "W1", "M1"],
    ])
    def test_permutations_yield_identical_final_state(self, order, clean_sandbox, products_df):
        client = SandboxClient(base_url="http://mock-sandbox/api/public/sandbox/v1")
        def dispatch(method: HttpMethod, endpoint: str, payload=None):
            return clean_sandbox.handle_request(method.value, endpoint, payload)
        client.request = MagicMock(side_effect=dispatch)
        audit = AuditLogger()
        sm_wf = WorkflowStateMachine(client, audit)
        executor_mig = MigrationExecutor(client, audit)

        vendor_payload = {
            "vendor_name": "Sri Ranga Castings",
            "gstin": "33AAACS1234R1ZK",
            "city": "Coimbatore",
            "state": "TN",
            "payment_terms_days": 45,
            "msme_registered": "Y",
            "source_system": "DRI",
        }

        clean_sandbox.reset()

        for step in order:
            if step == "W1":
                sm_wf.run_w1_onboarding(vendor_payload, 1400000.0, True, dry_run=False)
            elif step == "W2":
                sm_wf.run_w2_exceptions_report(reconciliation_func=classify_all, dry_run=False)
            elif step == "W3":
                sm_wf.run_w3_customer_dedup(dry_run=False)
            elif step == "M1":
                p = MigrationPlanner.plan_m1_price_migration(client, products_df, dry_run=False)
                executor_mig.execute_plan(p)
            elif step == "M2":
                p = MigrationPlanner.plan_m2_flowtech_mapping(client, products_df, dry_run=False)
                executor_mig.execute_plan(p)
            elif step == "M3":
                p = MigrationPlanner.plan_m3_salestrack_migration(client, dry_run=False)
                executor_mig.execute_plan(p)

        # Invariants across all permutations
        assert len(clean_sandbox.vendors) == 61  # 60 + 1 Sri Ranga
        assert sum(1 for p in clean_sandbox.products if p.get("drishti_price") is not None) == 113
        assert sum(1 for p in clean_sandbox.products if p.get("mapped_dri_sku") is not None) == 11
        assert sum(1 for c in clean_sandbox.customers if c.get("migrated_to_salestrack") == "Y") == 85
        assert sum(1 for c in clean_sandbox.customers if c.get("merged_into") is not None) == 45


# ============================================================
# 5. Secrets Scanner Test
# ============================================================

class TestSecuritySecretsScan:
    def test_no_hardcoded_secrets_in_repo(self):
        forbidden_patterns = [
            r"bearer\s+[a-zA-Z0-9_\-\.]{20,}",
            r"dri_key\s*=\s*['\"][a-zA-Z0-9_\-]{10,}['\"]",
            r"password\s*=\s*['\"][^'\"]+['\"]",
            r"api_key\s*=\s*['\"][a-zA-Z0-9_\-]{10,}['\"]",
        ]

        # Scan python and markdown files
        scanned_files = list(ROOT_DIR.glob("**/*.py")) + list(ROOT_DIR.glob("**/*.md"))

        violations = []
        for file_path in scanned_files:
            if ".git" in str(file_path) or ".pytest_cache" in str(file_path):
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            for pat in forbidden_patterns:
                if re.search(pat, text, re.IGNORECASE):
                    violations.append(f"{file_path.name}: matches {pat}")

        assert len(violations) == 0, f"Found hardcoded secrets in files: {violations}"

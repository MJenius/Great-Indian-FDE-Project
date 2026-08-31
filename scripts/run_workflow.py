#!/usr/bin/env python3
"""
run_workflow.py — CLI to run or dry-run W1, W2, W3 workflows against mock or real sandbox.

Usage:
    python scripts/run_workflow.py --task W1 --dry-run
    python scripts/run_workflow.py --task W2 --dry-run
    python scripts/run_workflow.py --task W3 --dry-run
    python scripts/run_workflow.py --task all --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.reconciliation.classifier import classify_all
from src.workflow.audit import AuditLogger
from src.workflow.client import SandboxClient
from src.workflow.models import HttpMethod
from src.workflow.state_machine import WorkflowStateMachine
from scripts.mock_sandbox import MockSandbox


def build_mock_client(data_dir: Path) -> SandboxClient:
    """Build a SandboxClient hooked directly to local MockSandbox."""
    mock_sb = MockSandbox(data_dir)
    client = SandboxClient(base_url="http://mock-sandbox/api/public/sandbox/v1")

    def mock_request(method: HttpMethod, endpoint: str, payload=None):
        return mock_sb.handle_request(method.value, endpoint, payload)

    client.request = MagicMock(side_effect=mock_request)
    return client


def main():
    parser = argparse.ArgumentParser(description="Run FDE Workflows (W1, W2, W3)")
    parser.add_argument("--task", choices=["W1", "W2", "W3", "all"], default="all", help="Workflow task to run")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Run in dry-run mode (no writes)")
    parser.add_argument("--data-dir", default="data", help="Path to data directory")
    parser.add_argument("--output-dir", default="outputs", help="Path to outputs directory")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = build_mock_client(data_dir)
    audit_logger = AuditLogger(log_file=output_dir / "workflow_audit.jsonl")
    sm = WorkflowStateMachine(client, audit_logger)

    tasks_to_run = ["W1", "W2", "W3"] if args.task == "all" else [args.task]

    for t in tasks_to_run:
        print(f"\n==========================================")
        print(f"RUNNING WORKFLOW {t} (dry_run={args.dry_run})")
        print(f"==========================================")

        if t == "W1":
            vendor_payload = {
                "vendor_name": "Sri Ranga Castings",
                "gstin": "33AAACS1234R1ZK",
                "city": "Coimbatore",
                "state": "TN",
                "payment_terms_days": 45,
                "msme_registered": "Y",
                "source_system": "DRI",
                "trial_po_cap": 200000.0,
            }
            plan = sm.run_w1_onboarding(
                vendor_details=vendor_payload,
                annual_spend=1400000.0,
                is_direct_material=True,
                dry_run=args.dry_run,
            )

        elif t == "W2":
            def recon_func(inv, po, vend):
                return classify_all(inv, po, vend)

            plan = sm.run_w2_exceptions_report(
                reconciliation_func=recon_func,
                dry_run=args.dry_run,
            )

        elif t == "W3":
            plan = sm.run_w3_customer_dedup(
                dry_run=args.dry_run,
            )

        plan_file = output_dir / f"workflow_{t.lower()}_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(plan.model_dump(), indent=2))

        print(f"Plan saved to: {plan_file}")
        print(f"Planned Actions: {len(plan.planned_actions)}")
        for a in plan.planned_actions:
            print(f"  [{a.method.value}] {a.endpoint} -> {a.description}")
        print(f"Status: {sm.state.value}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
run_migration.py — CLI to run or dry-run M1, M2, M3 migrations against mock or real sandbox.

Usage:
    python scripts/run_migration.py --task M1 --dry-run
    python scripts/run_migration.py --task M2 --dry-run
    python scripts/run_migration.py --task M3 --dry-run
    python scripts/run_migration.py --task all --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.migration.executors import MigrationExecutor
from src.migration.planners import MigrationPlanner
from src.workflow.audit import AuditLogger
from src.workflow.client import SandboxClient
from src.workflow.models import HttpMethod
from scripts.mock_sandbox import MockSandbox


def build_mock_client(data_dir: Path) -> tuple[SandboxClient, MockSandbox]:
    mock_sb = MockSandbox(data_dir)
    client = SandboxClient(base_url="http://mock-sandbox/api/public/sandbox/v1")

    def mock_request(method: HttpMethod, endpoint: str, payload=None):
        return mock_sb.handle_request(method.value, endpoint, payload)

    client.request = MagicMock(side_effect=mock_request)
    return client, mock_sb


def main():
    parser = argparse.ArgumentParser(description="Run DRI Migrations (M1, M2, M3)")
    parser.add_argument("--task", choices=["M1", "M2", "M3", "all"], default="all", help="Migration task to run")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Run in dry-run mode (no writes)")
    parser.add_argument("--data-dir", default="data", help="Path to data directory")
    parser.add_argument("--output-dir", default="outputs", help="Path to outputs directory")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client, mock_sb = build_mock_client(data_dir)
    audit_logger = AuditLogger(log_file=output_dir / "migration_audit.jsonl")
    executor = MigrationExecutor(client, audit_logger)

    products_df = pd.read_csv(data_dir / "products.csv")

    tasks_to_run = ["M1", "M2", "M3"] if args.task == "all" else [args.task]

    for t in tasks_to_run:
        print(f"\n==========================================")
        print(f"RUNNING MIGRATION {t} (dry_run={args.dry_run})")
        print(f"==========================================")

        if t == "M1":
            plan = MigrationPlanner.plan_m1_price_migration(
                client=client,
                products_df=products_df,
                dry_run=args.dry_run,
            )
            print(f"Total products in catalog: {plan.metadata['total_products']}")
            print(f"Products requiring update: {plan.metadata['products_requiring_update']}")
            print(f"Products with null 2023 price: {plan.metadata['products_with_null_2023_prices']}")
            print(f"Null price SKUs: {plan.metadata['null_price_skus']}")

        elif t == "M2":
            plan = MigrationPlanner.plan_m2_flowtech_mapping(
                client=client,
                products_df=products_df,
                dry_run=args.dry_run,
            )
            print(f"Total FlowTech products: {plan.metadata['total_flowtech_products']}")
            print(f"Unique matches: {plan.metadata['unique_matches']}")
            print(f"Review cases: {plan.metadata['review_cases']}")
            print(f"Proposed PATCH count: {plan.metadata['proposed_patch_count']}")
            for a in plan.flowtech_actions:
                clean_reason = a.reason.replace("₹", "INR ")
                print(f"  {a.flowtech_sku} -> {a.selected_dri_sku or a.status.value} ({clean_reason})")

        elif t == "M3":
            plan = MigrationPlanner.plan_m3_salestrack_migration(
                client=client,
                dry_run=args.dry_run,
            )
            print(f"Total customers in master: {plan.metadata['total_customers']}")
            print(f"Already migrated: {plan.metadata['already_migrated']}")
            print(f"Pending migration: {plan.metadata['pending_migration']}")
            print(f"Proposed PATCH count: {plan.metadata['proposed_patch_count']}")
            print(f"Generated CRM IDs: {plan.metadata['generated_crm_ids'][:5]} ...")

        # Save plan
        plan_file = output_dir / f"migration_{t.lower()}_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(plan.model_dump(), indent=2))

        # Execute
        success = executor.execute_plan(plan)
        print(f"Plan saved to: {plan_file}")
        print(f"Execution Success: {success}")


if __name__ == "__main__":
    main()

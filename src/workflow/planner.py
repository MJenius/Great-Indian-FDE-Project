"""
Deterministic planners for W1, W2, and W3 workflows.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
import pandas as pd

from .client import SandboxClient
from .models import HttpMethod, PlannedAction, WorkflowPlan
from .validators import WorkflowValidator


class WorkflowPlanner:
    """
    Generates deterministic execution plans for tasks W1, W2, and W3.
    """

    @staticmethod
    def plan_w1_onboarding(
        client: SandboxClient,
        vendor_details: Dict[str, Any],
        annual_spend: float = 1400000.0,
        is_direct_material: bool = True,
        dry_run: bool = True,
    ) -> WorkflowPlan:
        """
        Plan W1 vendor onboarding:
        1. Query existing vendors GET /erp/vendors
        2. Validate payload and determine approval matrix
        3. Plan POST /erp/vendors (if vendor doesn't already exist)
        4. Plan POST /erp/approvals for each required approver
        """
        status, vendors_data = client.request(HttpMethod.GET, "/erp/vendors")
        existing_vendors = vendors_data if isinstance(vendors_data, list) else []

        # Check if already exists by GSTIN or Name
        target_gstin = vendor_details.get("gstin", "").strip().upper()
        matching_vendor = None
        for v in existing_vendors:
            if str(v.get("gstin", "")).strip().upper() == target_gstin:
                matching_vendor = v
                break

        actions: List[PlannedAction] = []
        valid, errors, required_approvals = WorkflowValidator.validate_w1_vendor_payload(
            vendor_details, annual_spend, is_direct_material
        )
        if not valid:
            raise ValueError(f"W1 Validation failed: {errors}")

        if matching_vendor:
            # Vendor already exists - check if approvals are missing
            vendor_id = matching_vendor.get("vendor_id")
            for approver in required_approvals:
                actions.append(
                    PlannedAction(
                        action_id=f"approve_{approver.lower()}_{vendor_id}",
                        description=f"Record {approver} approval for existing vendor {vendor_id}",
                        method=HttpMethod.POST,
                        endpoint="/erp/approvals",
                        payload={
                            "entity_type": "VENDOR",
                            "entity_id": vendor_id,
                            "approver_role": approver,
                            "decision": "APPROVED",
                        },
                        expected_status=200,
                    )
                )
        else:
            # Vendor does not exist - create and approve
            actions.append(
                PlannedAction(
                    action_id="create_vendor_sri_ranga",
                    description="Create new vendor Sri Ranga Castings in DRISHTI ERP",
                    method=HttpMethod.POST,
                    endpoint="/erp/vendors",
                    payload=vendor_details,
                    expected_status=201,
                    verification_endpoint="/erp/vendors",
                )
            )
            for approver in required_approvals:
                actions.append(
                    PlannedAction(
                        action_id=f"approve_{approver.lower()}",
                        description=f"Record {approver} approval for Sri Ranga Castings",
                        method=HttpMethod.POST,
                        endpoint="/erp/approvals",
                        payload={
                            "entity_type": "VENDOR",
                            "vendor_gstin": target_gstin,
                            "approver_role": approver,
                            "decision": "APPROVED",
                        },
                        expected_status=200,
                    )
                )

        return WorkflowPlan(
            task="W1",
            dry_run=dry_run,
            planned_actions=actions,
            metadata={
                "vendor_details": vendor_details,
                "annual_spend": annual_spend,
                "is_direct_material": is_direct_material,
                "required_approvals": required_approvals,
                "already_existed": matching_vendor is not None,
            },
        )

    @staticmethod
    def plan_w2_exceptions_report(
        client: SandboxClient,
        reconciliation_func: Any,
        dry_run: bool = True,
    ) -> WorkflowPlan:
        """
        Plan W2 exceptions report:
        1. GET /erp/invoices and GET /erp/purchase_orders and GET /erp/vendors
        2. Run deterministic reconciliation engine
        3. Compute exception metrics and value at risk
        4. Validate report schema
        5. Plan POST /erp/reports/exceptions
        """
        status_inv, inv_data = client.request(HttpMethod.GET, "/erp/invoices")
        status_po, po_data = client.request(HttpMethod.GET, "/erp/purchase_orders")
        status_vend, vend_data = client.request(HttpMethod.GET, "/erp/vendors")

        df_inv = pd.DataFrame(inv_data)
        df_po = pd.DataFrame(po_data)
        df_vend = pd.DataFrame(vend_data)

        # Execute reconciliation
        results = reconciliation_func(df_inv, df_po, df_vend)
        statuses = [r["status"] for r in results]
        status_counts = pd.Series(statuses).value_counts().to_dict()

        total_inv = len(results)
        clean_inv = status_counts.get("CLEAN", 0)
        total_exc = total_inv - clean_inv

        # Value at risk calculation
        inv_indexed = df_inv.set_index("invoice_number")
        value_at_risk = 0.0
        for r in results:
            if r["status"] != "CLEAN":
                inv_num = r["invoice_number"]
                if inv_num in inv_indexed.index:
                    value_at_risk += float(inv_indexed.loc[inv_num, "invoice_total"])

        report_payload = {
            "total_invoices": total_inv,
            "clean_invoices": clean_inv,
            "total_exceptions": total_exc,
            "value_at_risk": round(value_at_risk, 2),
            "exceptions_by_class": {
                k: v for k, v in status_counts.items() if k != "CLEAN"
            },
        }

        valid, errors = WorkflowValidator.validate_w2_exceptions_report(report_payload)
        if not valid:
            raise ValueError(f"W2 Report validation failed: {errors}")

        actions = [
            PlannedAction(
                action_id="post_exceptions_report",
                description="Post full invoice reconciliation exceptions report to DRISHTI ERP",
                method=HttpMethod.POST,
                endpoint="/erp/reports/exceptions",
                payload=report_payload,
                expected_status=200,
            )
        ]

        return WorkflowPlan(
            task="W2",
            dry_run=dry_run,
            planned_actions=actions,
            metadata=report_payload,
        )

    @staticmethod
    def plan_w3_customer_dedup(
        client: SandboxClient,
        dry_run: bool = True,
    ) -> WorkflowPlan:
        """
        Plan W3 customer deduplication:
        1. GET /crm/customers
        2. Normalize customer names into identity groups
        3. Select earliest legacy_id as master
        4. Plan PATCH /crm/customers/{legacy_id} with merged_into for all duplicates
        """
        status_cust, cust_data = client.request(HttpMethod.GET, "/crm/customers")
        customers = cust_data if isinstance(cust_data, list) else []
        df = pd.DataFrame(customers)

        def norm_name(s: str) -> str:
            s = str(s).upper().strip()
            s = re.sub(r"\s*\((?:SOUTH|NORTH|II)\)\s*$", "", s)
            s = re.sub(r"[^A-Z0-9]", "", s)
            return s

        df["norm_name"] = df["customer_name"].apply(norm_name)
        # Sort by legacy_id to ensure deterministic earliest selection
        df = df.sort_values("legacy_id")

        actions: List[PlannedAction] = []
        cust_lookup = {c["legacy_id"]: c for c in customers}

        for norm_n, group in df.groupby("norm_name"):
            if len(group) > 1:
                # First one is original master
                master_id = group.iloc[0]["legacy_id"]
                duplicates = group.iloc[1:]
                for _, dup in duplicates.iterrows():
                    dup_id = dup["legacy_id"]
                    # If already merged into master, skip mutation (idempotent)
                    if dup.get("merged_into") == master_id:
                        continue

                    valid, errors = WorkflowValidator.validate_w3_customer_mutation(
                        dup_id, master_id, cust_lookup
                    )
                    if not valid:
                        raise ValueError(f"W3 mutation invalid: {errors}")

                    actions.append(
                        PlannedAction(
                            action_id=f"merge_{dup_id}_into_{master_id}",
                            description=f"Merge duplicate customer {dup_id} ({dup['customer_name']}) into master {master_id}",
                            method=HttpMethod.PATCH,
                            endpoint=f"/crm/customers/{dup_id}",
                            payload={"merged_into": master_id},
                            expected_status=200,
                            verification_endpoint=f"/crm/customers/{dup_id}",
                        )
                    )

        return WorkflowPlan(
            task="W3",
            dry_run=dry_run,
            planned_actions=actions,
            metadata={"total_customers": len(df), "planned_merges": len(actions)},
        )

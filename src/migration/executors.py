"""
Execution engine for Migration plans with validation, verification, and audit logging.
"""
from __future__ import annotations

from typing import Optional
from src.workflow.audit import AuditLogger
from src.workflow.client import SandboxClient, SandboxClientError
from src.workflow.models import HttpMethod, WorkflowState
from .models import MappingStatus, MigrationPlan
from .verifier import MigrationVerifier


class MigrationExecutor:
    def __init__(
        self,
        client: SandboxClient,
        audit_logger: AuditLogger,
    ):
        self.client = client
        self.audit = audit_logger

    def execute_plan(
        self,
        plan: MigrationPlan,
    ) -> bool:
        if plan.dry_run:
            self.audit.log(
                task=plan.task,
                state=WorkflowState.PLANNING,
                operation=HttpMethod.PATCH,
                endpoint=f"/migration/{plan.task.lower()}",
                target=plan.task,
                request_summary={"metadata": plan.metadata, "dry_run": True},
                result="DRY_RUN_PLANNED",
            )
            return True

        if plan.task == "M1":
            for action in plan.price_actions:
                self.audit.log(
                    task="M1",
                    state=WorkflowState.EXECUTING,
                    operation=HttpMethod.PATCH,
                    endpoint=f"/erp/products/{action.sku}",
                    target=action.sku,
                    request_summary={"drishti_price": action.desired_drishti_price},
                )
                try:
                    status, body = self.client.request(
                        HttpMethod.PATCH,
                        f"/erp/products/{action.sku}",
                        {"drishti_price": action.desired_drishti_price},
                    )
                    if status != 200:
                        return False
                    verified = MigrationVerifier.verify_price_patch(
                        self.client, action.sku, action.desired_drishti_price
                    )
                    if not verified:
                        return False
                except SandboxClientError:
                    return False
            return True

        elif plan.task == "M2":
            for action in plan.flowtech_actions:
                if action.action_type != "PATCH" or not action.selected_dri_sku:
                    continue

                self.audit.log(
                    task="M2",
                    state=WorkflowState.EXECUTING,
                    operation=HttpMethod.PATCH,
                    endpoint=f"/erp/products/{action.flowtech_sku}",
                    target=action.flowtech_sku,
                    request_summary={"mapped_dri_sku": action.selected_dri_sku},
                )
                try:
                    status, body = self.client.request(
                        HttpMethod.PATCH,
                        f"/erp/products/{action.flowtech_sku}",
                        {"mapped_dri_sku": action.selected_dri_sku},
                    )
                    if status != 200:
                        return False
                    verified = MigrationVerifier.verify_flowtech_mapping(
                        self.client, action.flowtech_sku, action.selected_dri_sku
                    )
                    if not verified:
                        return False
                except SandboxClientError:
                    return False
            return True

        elif plan.task == "M3":
            for action in plan.salestrack_actions:
                self.audit.log(
                    task="M3",
                    state=WorkflowState.EXECUTING,
                    operation=HttpMethod.PATCH,
                    endpoint=f"/crm/customers/{action.legacy_id}",
                    target=action.legacy_id,
                    request_summary={
                        "migrated_to_salestrack": action.desired_migrated_status,
                        "crm_id": action.desired_crm_id,
                    },
                )
                try:
                    status, body = self.client.request(
                        HttpMethod.PATCH,
                        f"/crm/customers/{action.legacy_id}",
                        {
                            "migrated_to_salestrack": action.desired_migrated_status,
                            "crm_id": action.desired_crm_id,
                        },
                    )
                    if status != 200:
                        return False
                    verified = MigrationVerifier.verify_salestrack_migration(
                        self.client, action.legacy_id, action.desired_crm_id
                    )
                    if not verified:
                        return False
                except SandboxClientError:
                    return False
            return True

        return False

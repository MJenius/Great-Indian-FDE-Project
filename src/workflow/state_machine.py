"""
Workflow State Machine coordinating the end-to-end task lifecycle.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional
from .audit import AuditLogger
from .client import SandboxClient
from .executor import WorkflowExecutor
from .models import WorkflowPlan, WorkflowState
from .planner import WorkflowPlanner


class WorkflowStateMachine:
    def __init__(
        self,
        client: SandboxClient,
        audit_logger: AuditLogger,
    ):
        self.client = client
        self.audit = audit_logger
        self.executor = WorkflowExecutor(client, audit_logger)
        self.state = WorkflowState.INIT

    def run_w1_onboarding(
        self,
        vendor_details: Dict[str, Any],
        annual_spend: float = 1400000.0,
        is_direct_material: bool = True,
        dry_run: bool = True,
    ) -> WorkflowPlan:
        self.state = WorkflowState.FETCHING
        self.state = WorkflowState.PLANNING
        plan = WorkflowPlanner.plan_w1_onboarding(
            client=self.client,
            vendor_details=vendor_details,
            annual_spend=annual_spend,
            is_direct_material=is_direct_material,
            dry_run=dry_run,
        )

        self.state = WorkflowState.VALIDATING
        self.state = WorkflowState.EXECUTING if not dry_run else WorkflowState.COMPLETED
        success = self.executor.execute_plan(plan)

        self.state = WorkflowState.COMPLETED if success else WorkflowState.FAILED
        return plan

    def run_w2_exceptions_report(
        self,
        reconciliation_func: Callable,
        dry_run: bool = True,
    ) -> WorkflowPlan:
        self.state = WorkflowState.FETCHING
        self.state = WorkflowState.PLANNING
        plan = WorkflowPlanner.plan_w2_exceptions_report(
            client=self.client,
            reconciliation_func=reconciliation_func,
            dry_run=dry_run,
        )

        self.state = WorkflowState.VALIDATING
        self.state = WorkflowState.EXECUTING if not dry_run else WorkflowState.COMPLETED
        success = self.executor.execute_plan(plan)

        self.state = WorkflowState.COMPLETED if success else WorkflowState.FAILED
        return plan

    def run_w3_customer_dedup(
        self,
        dry_run: bool = True,
    ) -> WorkflowPlan:
        self.state = WorkflowState.FETCHING
        self.state = WorkflowState.PLANNING
        plan = WorkflowPlanner.plan_w3_customer_dedup(
            client=self.client,
            dry_run=dry_run,
        )

        self.state = WorkflowState.VALIDATING
        self.state = WorkflowState.EXECUTING if not dry_run else WorkflowState.COMPLETED
        success = self.executor.execute_plan(plan)

        self.state = WorkflowState.COMPLETED if success else WorkflowState.FAILED
        return plan

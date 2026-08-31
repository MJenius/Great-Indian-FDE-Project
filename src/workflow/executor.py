"""
Execution engine that runs planned actions with state tracking, verification, and audit logging.
"""
from __future__ import annotations

from typing import List, Optional
from .audit import AuditLogger
from .client import SandboxClient, SandboxClientError
from .models import PlannedAction, WorkflowPlan, WorkflowState
from .verifier import WorkflowVerifier


class WorkflowExecutor:
    def __init__(
        self,
        client: SandboxClient,
        audit_logger: AuditLogger,
    ):
        self.client = client
        self.audit = audit_logger

    def execute_plan(
        self,
        plan: WorkflowPlan,
    ) -> bool:
        """
        Execute all planned actions sequentially with validation and verification.
        In dry_run mode, no mutations are executed.
        """
        if plan.dry_run:
            for action in plan.planned_actions:
                self.audit.log(
                    task=plan.task,
                    state=WorkflowState.PLANNING,
                    operation=action.method,
                    endpoint=action.endpoint,
                    target=action.action_id,
                    request_summary={"description": action.description, "payload": action.payload, "dry_run": True},
                    result="DRY_RUN_PLANNED",
                )
            return True

        for action in plan.planned_actions:
            self.audit.log(
                task=plan.task,
                state=WorkflowState.EXECUTING,
                operation=action.method,
                endpoint=action.endpoint,
                target=action.action_id,
                request_summary={"payload": action.payload},
            )

            try:
                status_code, resp_body = self.client.request(
                    method=action.method,
                    endpoint=action.endpoint,
                    payload=action.payload,
                )
                action.status_code = status_code
                action.response_body = resp_body
                action.executed = True

                if status_code != action.expected_status and not (200 <= status_code < 300):
                    err_msg = f"Unexpected status {status_code}, expected {action.expected_status}"
                    action.error = err_msg
                    self.audit.log(
                        task=plan.task,
                        state=WorkflowState.FAILED,
                        operation=action.method,
                        endpoint=action.endpoint,
                        target=action.action_id,
                        request_summary={"payload": action.payload},
                        status_code=status_code,
                        error=err_msg,
                    )
                    return False

                # Verification step
                is_verified = WorkflowVerifier.verify_action(self.client, action)
                action.verified = is_verified

                self.audit.log(
                    task=plan.task,
                    state=WorkflowState.VERIFYING if is_verified else WorkflowState.REQUIRES_REVIEW,
                    operation=action.method,
                    endpoint=action.endpoint,
                    target=action.action_id,
                    request_summary={"payload": action.payload},
                    status_code=status_code,
                    result="SUCCESS",
                    verified=is_verified,
                )

                if not is_verified:
                    return False

            except SandboxClientError as e:
                action.error = str(e)
                self.audit.log(
                    task=plan.task,
                    state=WorkflowState.FAILED,
                    operation=action.method,
                    endpoint=action.endpoint,
                    target=action.action_id,
                    request_summary={"payload": action.payload},
                    error=str(e),
                )
                return False

        return True

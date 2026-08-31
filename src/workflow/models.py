"""
Workflow models, state definitions, and data structures.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class WorkflowState(str, Enum):
    INIT = "INIT"
    FETCHING = "FETCHING"
    PLANNING = "PLANNING"
    VALIDATING = "VALIDATING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PATCH = "PATCH"


class PlannedAction(BaseModel):
    action_id: str
    description: str
    method: HttpMethod
    endpoint: str
    payload: Optional[Dict[str, Any]] = None
    expected_status: int = 200
    preconditions: List[str] = Field(default_factory=list)
    verification_endpoint: Optional[str] = None
    executed: bool = False
    status_code: Optional[int] = None
    response_body: Optional[Any] = None
    verified: bool = False
    error: Optional[str] = None


class WorkflowPlan(BaseModel):
    task: str  # W1, W2, W3
    dry_run: bool = True
    planned_actions: List[PlannedAction] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditEntry(BaseModel):
    timestamp: str
    task: str
    state: WorkflowState
    operation: HttpMethod
    endpoint: str
    target: str
    request_summary: Dict[str, Any]
    status_code: Optional[int] = None
    result: Optional[str] = None
    verified: bool = False
    error: Optional[str] = None

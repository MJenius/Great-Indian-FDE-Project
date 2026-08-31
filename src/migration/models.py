"""
Data models and action specifications for the Migration Engine.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MappingStatus(str, Enum):
    UNIQUE_MATCH = "UNIQUE_MATCH"
    NO_MATCH = "NO_MATCH"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"
    REVIEW = "REVIEW"


class PriceMigrationAction(BaseModel):
    sku: str
    current_drishti_price: Optional[float] = None
    desired_drishti_price: float
    reason: str
    action_type: str = "PATCH"


class FlowTechMappingAction(BaseModel):
    flowtech_sku: str
    normalized_description: str
    candidate_dri_skus: List[str] = Field(default_factory=list)
    selected_dri_sku: Optional[str] = None
    status: MappingStatus
    reason: str
    action_type: str = "PATCH"  # PATCH or NOOP/REVIEW


class SalesTrackCustomerAction(BaseModel):
    legacy_id: str
    customer_name: str
    current_migrated_status: str
    current_crm_id: Optional[str] = None
    desired_migrated_status: str
    desired_crm_id: str
    action_type: str = "PATCH"


class MigrationPlan(BaseModel):
    task: str  # M1, M2, M3
    dry_run: bool = True
    price_actions: List[PriceMigrationAction] = Field(default_factory=list)
    flowtech_actions: List[FlowTechMappingAction] = Field(default_factory=list)
    salestrack_actions: List[SalesTrackCustomerAction] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

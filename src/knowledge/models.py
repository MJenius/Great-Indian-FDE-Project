"""
Knowledge Engine data models for policy rules, questions, evidence, and answers.
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PolicyDocumentCode(str, Enum):
    PP_2019 = "PP-2019"
    PP_2023 = "PP-2023"
    WRP_2020 = "WRP-2020"
    VOS_7 = "VOS-7"


class PolicyDomain(str, Enum):
    PRICING_DISCOUNT = "PRICING_DISCOUNT"
    CREDIT_TERMS = "CREDIT_TERMS"
    FREIGHT = "FREIGHT"
    PRICE_REVISION_NOTICE = "PRICE_REVISION_NOTICE"
    WARRANTY = "WARRANTY"
    RETURNS_RESTOCKING = "RETURNS_RESTOCKING"
    VENDOR_ONBOARDING = "VENDOR_ONBOARDING"


class PolicyEvidence(BaseModel):
    document_code: PolicyDocumentCode
    section: str
    page: int
    text_excerpt: str


class PolicyRule(BaseModel):
    rule_id: str
    domain: PolicyDomain
    document_code: PolicyDocumentCode
    effective_from: date
    effective_until: Optional[date] = None
    superseded_by: Optional[PolicyDocumentCode] = None
    section: str
    page: int
    description: str
    evidence_text: str
    rule_payload: Dict[str, Any] = Field(default_factory=dict)


class QuestionInterpretation(BaseModel):
    qid: str
    raw_question: str
    domain: PolicyDomain
    explicit_date: Optional[date] = None
    is_historical: bool = False
    is_current: bool = True
    distributor_tier: Optional[str] = None
    order_value: Optional[float] = None
    is_flowtech: bool = False
    is_pre_acquisition_stock: bool = False
    dispatch_date: Optional[date] = None
    commissioning_date: Optional[date] = None
    annual_spend: Optional[float] = None
    is_direct_material: bool = False


class KnowledgeAnswer(BaseModel):
    qid: str
    answer: str
    governing_source: str
    confidence: float = 1.0
    status: str = "ANSWERED"  # ANSWERED, AMBIGUOUS, UNSUPPORTED, CONFLICTING
    rule_id: Optional[str] = None
    evidence_text: Optional[str] = None
    resolution_notes: Optional[str] = None
    why_this_source: Optional[str] = None
    why_other_sources_rejected: Optional[str] = None

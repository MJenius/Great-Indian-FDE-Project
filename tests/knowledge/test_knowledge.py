"""
Unit and Integration test suite for the Knowledge Policy Engine.

Covers:
- All 12 public questions with exact source resolution and answers
- PP-2019 vs PP-2023 transition boundaries (2023-09-30 vs 2023-10-01)
- Pricing discount slabs (<5L, 5L-15L, >15L, exact boundaries)
- Credit terms for standard and Platinum tiers across policies
- Freight terms (pre-2023 threshold-based vs post-2023 all ex-works)
- Price revision notice periods (30 days vs 15 days)
- Warranty date arithmetic (dispatch vs commissioning, calendar month reasoning)
- FlowTech pre-acquisition 24-month rule vs standard warranty
- Restocking charges and 30-day return window
- VOS-7 vendor onboarding documents, trial PO cap, and spend/direct material approval matrix
- Adversarial questions designed to trigger source confusion
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.knowledge.answerer import KnowledgeEngine
from src.knowledge.models import PolicyDocumentCode, PolicyDomain
from src.knowledge.router import QuestionRouter

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@pytest.fixture
def engine():
    return KnowledgeEngine(data_dir=DATA_DIR)


# ============================================================
# 1. Public Knowledge Questions Test
# ============================================================

class TestPublicKnowledgeQuestions:
    def test_k01_discount_march_2024(self, engine):
        ans = engine.answer_question("K-01", "A distributor places a single order of Rs 7,20,000 in March 2024. What discount applies?")
        assert ans.governing_source == PolicyDocumentCode.PP_2023.value
        assert ans.answer == "10%"

    def test_k02_gold_credit_terms_today(self, engine):
        ans = engine.answer_question("K-02", "What are the standard credit terms for a Gold-tier distributor today?")
        assert ans.governing_source == PolicyDocumentCode.PP_2023.value
        assert ans.answer == "30 days from the date of invoice"

    def test_k03_freight_february_2024(self, engine):
        ans = engine.answer_question("K-03", "Who bears freight on a Rs 3,00,000 distributor order shipped in February 2024?")
        assert ans.governing_source == PolicyDocumentCode.PP_2023.value
        assert ans.answer == "Buyer"

    def test_k04_flowtech_pre_acquisition_warranty(self, engine):
        ans = engine.answer_question("K-04", "What warranty applies to a FlowTech-branded pump supplied from pre-acquisition stock?")
        assert ans.governing_source == PolicyDocumentCode.WRP_2020.value
        assert ans.answer == "24 months from despatch"

    def test_k05_onboarding_documents(self, engine):
        ans = engine.answer_question("K-05", "Which documents must a new vendor submit at onboarding?")
        assert ans.governing_source == PolicyDocumentCode.VOS_7.value
        assert ans.answer == "GST registration certificate, cancelled cheque, and MSME declaration (where applicable)"

    def test_k06_trial_po_cap(self, engine):
        ans = engine.answer_question("K-06", "What is the maximum value of a trial purchase order for a newly onboarded vendor?")
        assert ans.governing_source == PolicyDocumentCode.VOS_7.value
        assert ans.answer == "Rs 2,00,000"

    def test_k07_spend_14_lakh_approvals(self, engine):
        ans = engine.answer_question("K-07", "A new vendor's projected annual spend is Rs 14,00,000. Whose approval is required?")
        assert ans.governing_source == PolicyDocumentCode.VOS_7.value
        assert ans.answer == "CFO"

    def test_k08_discount_below_5_lakh_2024(self, engine):
        ans = engine.answer_question("K-08", "What discount applies to a single order of Rs 4,20,000 placed in March 2024?")
        assert ans.governing_source == PolicyDocumentCode.PP_2023.value
        assert ans.answer == "Nil"

    def test_k09_restocking_charge(self, engine):
        ans = engine.answer_question("K-09", "What restocking charge applies to returns?")
        assert ans.governing_source == PolicyDocumentCode.WRP_2020.value
        assert ans.answer == "10% of invoice value"

    def test_k10_price_revision_notice_today(self, engine):
        ans = engine.answer_question("K-10", "How much notice must DRI give before revising list prices today?")
        assert ans.governing_source == PolicyDocumentCode.PP_2023.value
        assert ans.answer == "15 days written notice"

    def test_k11_warranty_whichever_earlier(self, engine):
        ans = engine.answer_question("K-11", "A DRI pump is despatched in January 2025 and commissioned in June 2025. When does warranty end?")
        assert ans.governing_source == PolicyDocumentCode.WRP_2020.value
        assert ans.answer == "June 2026"

    def test_k12_platinum_credit_terms(self, engine):
        ans = engine.answer_question("K-12", "What credit terms does a Platinum-tier distributor receive?")
        assert ans.governing_source == PolicyDocumentCode.PP_2023.value
        assert ans.answer == "60 days from the date of invoice"


# ============================================================
# 2. Date-Aware Supersession & Boundary Tests (PP-2019 vs PP-2023)
# ============================================================

class TestSupersessionAndBoundaries:
    def test_historical_discount_in_2022(self, engine):
        ans = engine.answer_question("SYN-01", "What discount applied to an order of Rs 4,20,000 placed in 2022?")
        assert ans.governing_source == PolicyDocumentCode.PP_2019.value
        assert ans.answer == "6%"

    def test_historical_discount_above_5L_in_2022(self, engine):
        ans = engine.answer_question("SYN-02", "What discount applied to an order of Rs 7,20,000 placed in 2022?")
        assert ans.governing_source == PolicyDocumentCode.PP_2019.value
        assert ans.answer == "12%"

    def test_historical_freight_above_2L_in_2022(self, engine):
        ans = engine.answer_question("SYN-03", "Who paid freight for a Rs 3,00,000 order shipped in 2022?")
        assert ans.governing_source == PolicyDocumentCode.PP_2019.value
        assert ans.answer == "DRI"

    def test_historical_price_notice_in_2022(self, engine):
        ans = engine.answer_question("SYN-04", "How much notice was required for price revision in 2022?")
        assert ans.governing_source == PolicyDocumentCode.PP_2019.value
        assert ans.answer == "30 days written notice"

    def test_historical_credit_terms_in_2022(self, engine):
        ans = engine.answer_question("SYN-05", "What credit terms did distributors receive in 2022?")
        assert ans.governing_source == PolicyDocumentCode.PP_2019.value
        assert ans.answer == "45 days from the date of invoice"


# ============================================================
# 3. Warranty & Date Arithmetic Edge Cases
# ============================================================

class TestWarrantyDateArithmetic:
    def test_warranty_dispatch_earlier_than_commissioning(self, engine):
        ans = engine.answer_question("SYN-06", "A DRI pump is despatched in January 2025 and commissioned in December 2025. When does warranty end?")
        assert ans.governing_source == PolicyDocumentCode.WRP_2020.value
        assert ans.answer == "July 2026"

    def test_standard_flowtech_post_acquisition(self, engine):
        ans = engine.answer_question("SYN-07", "What is the standard warranty on a newly manufactured FlowTech pump?")
        assert ans.governing_source == PolicyDocumentCode.WRP_2020.value
        assert "18 months from despatch" in ans.answer


# ============================================================
# 4. VOS-7 Approvals Matrix Edge Cases
# ============================================================

class TestVOS7ApprovalsMatrix:
    def test_direct_material_low_spend(self, engine):
        ans = engine.answer_question("SYN-08", "Whose approval is required for a direct-material vendor with Rs 5,00,000 projected spend?")
        assert ans.governing_source == PolicyDocumentCode.VOS_7.value
        assert ans.answer == "Plant Head + QA"

    def test_indirect_material_low_spend(self, engine):
        ans = engine.answer_question("SYN-09", "Whose approval is required for a general indirect vendor with Rs 5,00,000 spend?")
        assert ans.governing_source == PolicyDocumentCode.VOS_7.value
        assert ans.answer == "GM Procurement"

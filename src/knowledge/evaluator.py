"""
Deterministic Policy Rule Evaluator.
Executes mathematical discount slabs, calendar-aware date arithmetic, approval matrices, and policy queries.
"""
from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional
from dateutil.relativedelta import relativedelta

from .models import KnowledgeAnswer, PolicyDocumentCode, PolicyDomain, PolicyRule, QuestionInterpretation


class PolicyEvaluator:
    @classmethod
    def evaluate_rule(
        cls,
        interp: QuestionInterpretation,
        rule: PolicyRule,
        why_this: str,
        why_other: str,
    ) -> KnowledgeAnswer:
        domain = rule.domain
        ans_text = ""

        # 1. PRICING DISCOUNTS
        if domain == PolicyDomain.PRICING_DISCOUNT:
            val = Decimal(str(interp.order_value or 0.0))
            if rule.document_code == PolicyDocumentCode.PP_2023:
                if val < Decimal("500000.00"):
                    ans_text = "Nil"
                elif Decimal("500000.00") <= val <= Decimal("1500000.00"):
                    ans_text = "10%"
                else:
                    ans_text = "14%"
            elif rule.document_code == PolicyDocumentCode.PP_2019:
                if val < Decimal("100000.00"):
                    ans_text = "Nil"
                elif Decimal("100000.00") <= val <= Decimal("500000.00"):
                    ans_text = "6%"
                else:
                    ans_text = "12%"

        # 2. CREDIT TERMS
        elif domain == PolicyDomain.CREDIT_TERMS:
            if rule.document_code == PolicyDocumentCode.PP_2023:
                if interp.distributor_tier == "Platinum":
                    ans_text = "60 days from the date of invoice"
                else:
                    ans_text = "30 days from the date of invoice"
            elif rule.document_code == PolicyDocumentCode.PP_2019:
                ans_text = "45 days from the date of invoice"

        # 3. FREIGHT
        elif domain == PolicyDomain.FREIGHT:
            if rule.document_code == PolicyDocumentCode.PP_2023:
                ans_text = "Buyer"
            elif rule.document_code == PolicyDocumentCode.PP_2019:
                val = Decimal(str(interp.order_value or 0.0))
                if val > Decimal("200000.00"):
                    ans_text = "DRI"
                else:
                    ans_text = "Buyer"

        # 4. PRICE REVISION NOTICE
        elif domain == PolicyDomain.PRICE_REVISION_NOTICE:
            if rule.document_code == PolicyDocumentCode.PP_2023:
                ans_text = "15 days written notice"
            elif rule.document_code == PolicyDocumentCode.PP_2019:
                ans_text = "30 days written notice"

        # 5. RETURNS & RESTOCKING
        elif domain == PolicyDomain.RETURNS_RESTOCKING:
            ans_text = "10% of invoice value"

        # 6. WARRANTY
        elif domain == PolicyDomain.WARRANTY:
            if interp.is_flowtech and interp.is_pre_acquisition_stock:
                ans_text = "24 months from despatch"
            elif interp.dispatch_date and interp.commissioning_date:
                # Calendar-aware month arithmetic
                # 18 months from despatch vs 12 months from commissioning
                d_end = interp.dispatch_date + relativedelta(months=18)
                c_end = interp.commissioning_date + relativedelta(months=12)

                # whichever is earlier
                if d_end <= c_end:
                    earlier = d_end
                else:
                    earlier = c_end

                ans_text = f"{earlier.strftime('%B %Y')}"
            else:
                ans_text = "18 months from despatch or 12 months from commissioning, whichever is earlier"

        # 7. VENDOR ONBOARDING
        elif domain == PolicyDomain.VENDOR_ONBOARDING:
            q_low = interp.raw_question.lower()
            if "document" in q_low:
                ans_text = "GST registration certificate, cancelled cheque, and MSME declaration (where applicable)"
            elif "trial purchase order" in q_low or "trial po" in q_low:
                ans_text = "Rs 2,00,000"
            elif "approval" in q_low or "spend" in q_low:
                spend = Decimal(str(interp.annual_spend or 0.0))
                if spend > Decimal("1000000.00"):
                    ans_text = "CFO"
                elif interp.is_direct_material:
                    ans_text = "Plant Head + QA"
                else:
                    ans_text = "GM Procurement"

        return KnowledgeAnswer(
            qid=interp.qid,
            answer=ans_text,
            governing_source=rule.document_code.value,
            confidence=1.0,
            status="ANSWERED",
            rule_id=rule.rule_id,
            evidence_text=rule.evidence_text,
            resolution_notes=f"Evaluated via rule {rule.rule_id} from {rule.section} (page {rule.page})",
            why_this_source=why_this,
            why_other_sources_rejected=why_other,
        )

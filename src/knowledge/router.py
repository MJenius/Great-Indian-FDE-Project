"""
Deterministic Question Router & Intent Parser.
Extracts entities, amounts, dates, and domain intents from policy questions.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Optional
from .models import PolicyDomain, QuestionInterpretation


class QuestionRouter:
    MONTH_MAP = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }

    @classmethod
    def parse_question(cls, qid: str, text: str) -> QuestionInterpretation:
        q_lower = text.lower()

        # 1. Determine Domain Intent
        domain = cls._classify_domain(q_lower)

        # 2. Extract Monetary Amounts (e.g. Rs 7,20,000 or Rs 14,00,000)
        order_val = cls._extract_inr_amount(text)

        # 3. Extract Explicit Dates (e.g. March 2024, February 2024, 2022)
        exp_date = cls._extract_explicit_date(q_lower)

        # 4. Check Historical vs Current keywords
        is_hist = bool(re.search(r"\b(in 2019|in 2020|in 2021|in 2022|prior to|historically|under pp-2019)\b", q_lower))
        is_curr = bool(re.search(r"\b(today|currently|now|revised|pp-2023|2024|2025|2026)\b", q_lower)) or (not is_hist and exp_date is None)

        # 5. Extract Distributor Tier
        dist_tier = None
        if "platinum" in q_lower:
            dist_tier = "Platinum"
        elif "gold" in q_lower:
            dist_tier = "Gold"
        elif "silver" in q_lower:
            dist_tier = "Silver"

        # 6. Extract FlowTech / Warranty specifics
        is_flowtech = "flowtech" in q_lower
        is_pre_acq = "pre-acquisition" in q_lower or "pre acquisition" in q_lower

        dispatch_dt = cls._extract_event_date(text, r"despatch(?:ed)?\s+in\s+([A-Za-z]+\s+\d{4})")
        comm_dt = cls._extract_event_date(text, r"commission(?:ed)?\s+in\s+([A-Za-z]+\s+\d{4})")

        # 7. Vendor Onboarding specifics
        is_direct = "direct-material" in q_lower or "direct material" in q_lower

        return QuestionInterpretation(
            qid=qid,
            raw_question=text,
            domain=domain,
            explicit_date=exp_date,
            is_historical=is_hist,
            is_current=is_curr,
            distributor_tier=dist_tier,
            order_value=order_val,
            is_flowtech=is_flowtech,
            is_pre_acquisition_stock=is_pre_acq,
            dispatch_date=dispatch_dt,
            commissioning_date=comm_dt,
            annual_spend=order_val,
            is_direct_material=is_direct,
        )

    @classmethod
    def _classify_domain(cls, q_lower: str) -> PolicyDomain:
        if any(k in q_lower for k in ["discount", "single order"]):
            return PolicyDomain.PRICING_DISCOUNT
        if any(k in q_lower for k in ["credit terms", "credit"]):
            return PolicyDomain.CREDIT_TERMS
        if any(k in q_lower for k in ["freight", "shipping", "transport", "ex-works", "for destination"]):
            return PolicyDomain.FREIGHT
        if any(k in q_lower for k in ["notice", "revising list prices", "price revision"]):
            return PolicyDomain.PRICE_REVISION_NOTICE
        if any(k in q_lower for k in ["restocking", "return", "returns"]):
            return PolicyDomain.RETURNS_RESTOCKING
        if any(k in q_lower for k in ["warranty", "defect", "commissioned"]):
            return PolicyDomain.WARRANTY
        if any(k in q_lower for k in ["vendor", "onboarding", "trial purchase order", "trial po", "documents must a new vendor"]):
            return PolicyDomain.VENDOR_ONBOARDING

        # Default fallback
        return PolicyDomain.PRICING_DISCOUNT

    @classmethod
    def _extract_inr_amount(cls, text: str) -> Optional[float]:
        # Matches Rs 7,20,000 or Rs. 14,00,000 or 720000
        m = re.search(r"(?:Rs\.?|INR)\s*([\d,]+)", text, flags=re.IGNORECASE)
        if m:
            clean = m.group(1).replace(",", "")
            return float(Decimal(clean))
        return None

    @classmethod
    def _extract_explicit_date(cls, q_lower: str) -> Optional[date]:
        m = re.search(r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})\b", q_lower)
        if m:
            mon_str = m.group(1).lower()
            year = int(m.group(2))
            month = cls.MONTH_MAP[mon_str]
            return date(year, month, 1)

        m_yr = re.search(r"\b(2019|2020|2021|2022|2023|2024|2025|2026)\b", q_lower)
        if m_yr:
            return date(int(m_yr.group(1)), 1, 1)
        return None

    @classmethod
    def _extract_event_date(cls, text: str, pattern: str) -> Optional[date]:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            parts = m.group(1).strip().split()
            if len(parts) == 2:
                mon_str = parts[0].lower()
                year = int(parts[1])
                if mon_str in cls.MONTH_MAP:
                    return date(year, cls.MONTH_MAP[mon_str], 1)
        return None

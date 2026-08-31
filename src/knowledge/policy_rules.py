"""
Canonical Structured Policy Rules extracted from official DRI policy documents.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, List
from .models import PolicyDocumentCode, PolicyDomain, PolicyRule


def build_canonical_policy_rules() -> List[PolicyRule]:
    rules: List[PolicyRule] = []

    # ========================================================
    # 1. PP-2019 Rules (Effective 2019-04-01 to 2023-09-30)
    # ========================================================
    # PP-2019 Discounts
    rules.append(
        PolicyRule(
            rule_id="PP-2019-DISCOUNT",
            domain=PolicyDomain.PRICING_DISCOUNT,
            document_code=PolicyDocumentCode.PP_2019,
            effective_from=date(2019, 4, 1),
            effective_until=date(2023, 9, 30),
            superseded_by=PolicyDocumentCode.PP_2023,
            section="2. Distributor discounts",
            page=1,
            description="Distributor discounts per single order value (PP-2019)",
            evidence_text="Single order value: Below Rs 1,00,000 -> Nil; Rs 1,00,000 - Rs 5,00,000 -> 6%; Above Rs 5,00,000 -> 12% flat",
            rule_payload={
                "slabs": [
                    {"max": Decimal("100000.00"), "inclusive": False, "discount_pct": Decimal("0.0")},
                    {"min": Decimal("100000.00"), "max": Decimal("500000.00"), "discount_pct": Decimal("6.0")},
                    {"min": Decimal("500000.00"), "inclusive": False, "discount_pct": Decimal("12.0")},
                ]
            },
        )
    )

    # PP-2019 Credit Terms
    rules.append(
        PolicyRule(
            rule_id="PP-2019-CREDIT",
            domain=PolicyDomain.CREDIT_TERMS,
            document_code=PolicyDocumentCode.PP_2019,
            effective_from=date(2019, 4, 1),
            effective_until=date(2023, 9, 30),
            superseded_by=PolicyDocumentCode.PP_2023,
            section="3. Credit terms",
            page=1,
            description="45 days credit from date of invoice irrespective of tier",
            evidence_text="3.1 All authorised distributors in good standing are extended credit of 45 days from the date of invoice, irrespective of tier.",
            rule_payload={"standard_credit_days": 45, "tier_specific": False},
        )
    )

    # PP-2019 Freight
    rules.append(
        PolicyRule(
            rule_id="PP-2019-FREIGHT",
            domain=PolicyDomain.FREIGHT,
            document_code=PolicyDocumentCode.PP_2019,
            effective_from=date(2019, 4, 1),
            effective_until=date(2023, 9, 30),
            superseded_by=PolicyDocumentCode.PP_2023,
            section="4. Freight",
            page=1,
            description="Orders above Rs 2,00,000 FOR destination (borne by DRI); below is freight-to-pay",
            evidence_text="4.1 For single orders above Rs 2,00,000, despatch is FOR destination and freight is borne by DRI. Orders below this value are despatched freight-to-pay.",
            rule_payload={"free_freight_threshold": Decimal("200000.00"), "free_freight_bearer": "DRI"},
        )
    )

    # PP-2019 Notice
    rules.append(
        PolicyRule(
            rule_id="PP-2019-NOTICE",
            domain=PolicyDomain.PRICE_REVISION_NOTICE,
            document_code=PolicyDocumentCode.PP_2019,
            effective_from=date(2019, 4, 1),
            effective_until=date(2023, 9, 30),
            superseded_by=PolicyDocumentCode.PP_2023,
            section="5. Price revisions",
            page=1,
            description="Minimum 30 days written notice before list price revision",
            evidence_text="5.1 DRI will provide a minimum of 30 days written notice before any revision to the list price.",
            rule_payload={"notice_days": 30},
        )
    )

    # ========================================================
    # 2. PP-2023 Rules (Effective 2023-10-01 onwards)
    # ========================================================
    # PP-2023 Discounts
    rules.append(
        PolicyRule(
            rule_id="PP-2023-DISCOUNT",
            domain=PolicyDomain.PRICING_DISCOUNT,
            document_code=PolicyDocumentCode.PP_2023,
            effective_from=date(2023, 10, 1),
            section="2. Distributor discounts",
            page=1,
            description="Revised distributor discounts per single order value (PP-2023)",
            evidence_text="Single order value: Below Rs 5,00,000 -> Nil; Rs 5,00,000 - Rs 15,00,000 -> 10%; Above Rs 15,00,000 -> 14%",
            rule_payload={
                "slabs": [
                    {"max": Decimal("500000.00"), "inclusive": False, "discount_pct": Decimal("0.0")},
                    {"min": Decimal("500000.00"), "max": Decimal("1500000.00"), "discount_pct": Decimal("10.0")},
                    {"min": Decimal("1500000.00"), "inclusive": False, "discount_pct": Decimal("14.0")},
                ]
            },
        )
    )

    # PP-2023 Credit Terms
    rules.append(
        PolicyRule(
            rule_id="PP-2023-CREDIT",
            domain=PolicyDomain.CREDIT_TERMS,
            document_code=PolicyDocumentCode.PP_2023,
            effective_from=date(2023, 10, 1),
            section="3. Credit terms",
            page=1,
            description="Standard credit 30 days; Platinum-tier 60 days",
            evidence_text="3.1 Standard credit is 30 days from the date of invoice. Platinum-tier distributors are extended 60 days.",
            rule_payload={"standard_credit_days": 30, "platinum_credit_days": 60, "tier_specific": True},
        )
    )

    # PP-2023 Freight
    rules.append(
        PolicyRule(
            rule_id="PP-2023-FREIGHT",
            domain=PolicyDomain.FREIGHT,
            document_code=PolicyDocumentCode.PP_2023,
            effective_from=date(2023, 10, 1),
            section="4. Freight",
            page=1,
            description="All despatches are ex-works; freight, insurance, unloading to buyer's account",
            evidence_text="4.1 All despatches are ex-works. Freight, transit insurance and unloading are to the buyer's account irrespective of order value.",
            rule_payload={"all_ex_works": True, "bearer": "Buyer"},
        )
    )

    # PP-2023 Notice
    rules.append(
        PolicyRule(
            rule_id="PP-2023-NOTICE",
            domain=PolicyDomain.PRICE_REVISION_NOTICE,
            document_code=PolicyDocumentCode.PP_2023,
            effective_from=date(2023, 10, 1),
            section="5. Price revisions",
            page=1,
            description="Minimum 15 days written notice before list price revision",
            evidence_text="5.1 DRI will provide a minimum of 15 days written notice before any revision to the list price.",
            rule_payload={"notice_days": 15},
        )
    )

    # ========================================================
    # 3. WRP-2020 Rules (Effective 2020-01-01 onwards)
    # ========================================================
    # Standard Warranty
    rules.append(
        PolicyRule(
            rule_id="WRP-2020-WARRANTY-STD",
            domain=PolicyDomain.WARRANTY,
            document_code=PolicyDocumentCode.WRP_2020,
            effective_from=date(2020, 1, 1),
            section="1. Warranty",
            page=1,
            description="Standard DRI warranty: 18 months from despatch or 12 months from commissioning, whichever is earlier",
            evidence_text="1.1 All products are warranted against manufacturing defects for 18 months from the date of despatch or 12 months from the date of commissioning, whichever is earlier.",
            rule_payload={"months_from_despatch": 18, "months_from_commissioning": 12, "whichever_earlier": True},
        )
    )

    # FlowTech Addendum Warranty
    rules.append(
        PolicyRule(
            rule_id="WRP-2020-WARRANTY-FLOWTECH",
            domain=PolicyDomain.WARRANTY,
            document_code=PolicyDocumentCode.WRP_2020,
            effective_from=date(2020, 1, 1),
            section="Addendum A - FlowTech Products",
            page=2,
            description="FlowTech-branded products from pre-acquisition stock have 24 months warranty from despatch",
            evidence_text="Addendum A: warranty on FlowTech-branded products already committed to the market will continue to be honoured at 24 months from despatch until existing stock is exhausted.",
            rule_payload={"flowtech_pre_acquisition_months": 24},
        )
    )

    # Returns & Restocking
    rules.append(
        PolicyRule(
            rule_id="WRP-2020-RETURNS",
            domain=PolicyDomain.RETURNS_RESTOCKING,
            document_code=PolicyDocumentCode.WRP_2020,
            effective_from=date(2020, 1, 1),
            section="3. Returns",
            page=1,
            description="Return window 30 days of despatch; restocking charge 10% of invoice value",
            evidence_text="3.1 Unused goods in original packing may be returned within 30 days of despatch against a restocking charge of 10% of invoice value. Made-to-order items are not returnable.",
            rule_payload={"return_window_days": 30, "restocking_charge_pct": Decimal("10.0")},
        )
    )

    # ========================================================
    # 4. VOS-7 Rules (Effective 2021-06-15 onwards)
    # ========================================================
    # Onboarding Documents & Trial PO
    rules.append(
        PolicyRule(
            rule_id="VOS-7-DOCS-TRIAL",
            domain=PolicyDomain.VENDOR_ONBOARDING,
            document_code=PolicyDocumentCode.VOS_7,
            effective_from=date(2021, 6, 15),
            section="2. Procedure",
            page=1,
            description="Onboarding documents and trial PO cap of Rs 2,00,000",
            evidence_text="Step 2: Collect GST registration certificate, cancelled cheque, and MSME declaration (where applicable). Step 6: Trial purchase order, capped at Rs 2,00,000.",
            rule_payload={
                "required_documents": ["GST registration certificate", "cancelled cheque", "MSME declaration (where applicable)"],
                "trial_po_cap": Decimal("200000.00"),
            },
        )
    )

    # Approval Matrix
    rules.append(
        PolicyRule(
            rule_id="VOS-7-APPROVALS",
            domain=PolicyDomain.VENDOR_ONBOARDING,
            document_code=PolicyDocumentCode.VOS_7,
            effective_from=date(2021, 6, 15),
            section="3. Approval matrix",
            page=1,
            description="Approval matrix: Annual spend > 10L requires CFO; Direct-material requires Plant Head + QA; Others GM Procurement",
            evidence_text="Projected annual spend above Rs 10,00,000 -> CFO; Direct-material vendor (any value) -> Plant Head + QA; All other vendors -> GM Procurement",
            rule_payload={
                "spend_threshold": Decimal("1000000.00"),
                "cfo_condition": "spend > 10,00,000",
                "direct_material_approvers": ["Plant Head", "QA"],
                "default_approver": "GM Procurement",
            },
        )
    )

    return rules

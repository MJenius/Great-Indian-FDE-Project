"""
Policy Resolver determining exact governing source based on effective dates, supersession, and domain.
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional, Tuple
from .models import PolicyDocumentCode, PolicyDomain, PolicyRule, QuestionInterpretation


class PolicyResolver:
    """
    Resolves which specific policy document governs a parsed question.
    """

    PP_2023_EFFECTIVE_DATE = date(2023, 10, 1)

    @classmethod
    def resolve_governing_rule(
        cls,
        interp: QuestionInterpretation,
        all_rules: List[PolicyRule],
    ) -> Tuple[PolicyRule, str, str]:
        """
        Determines the governing rule and returns:
        (selected_rule, why_this_source, why_other_sources_rejected)
        """
        domain_rules = [r for r in all_rules if r.domain == interp.domain]

        # 1. Vendor Onboarding Domain -> VOS-7
        if interp.domain == PolicyDomain.VENDOR_ONBOARDING:
            vos_rules = [r for r in domain_rules if r.document_code == PolicyDocumentCode.VOS_7]
            if "approval" in interp.raw_question.lower() or "spend" in interp.raw_question.lower():
                rule = next(r for r in vos_rules if r.rule_id == "VOS-7-APPROVALS")
            else:
                rule = next(r for r in vos_rules if r.rule_id == "VOS-7-DOCS-TRIAL")
            return (
                rule,
                "VOS-7 is the sole standard operating procedure governing vendor onboarding, documents, trial POs, and approvals.",
                "PP-2019, PP-2023, and WRP-2020 govern distributor pricing and warranty, not vendor onboarding.",
            )

        # 2. Warranty and Returns Domain -> WRP-2020
        if interp.domain in (PolicyDomain.WARRANTY, PolicyDomain.RETURNS_RESTOCKING):
            wrp_rules = [r for r in domain_rules if r.document_code == PolicyDocumentCode.WRP_2020]
            if interp.is_flowtech and interp.is_pre_acquisition_stock:
                rule = next(r for r in wrp_rules if r.rule_id == "WRP-2020-WARRANTY-FLOWTECH")
                why = "WRP-2020 Addendum A explicitly governs warranty for FlowTech products supplied from pre-acquisition stock."
            elif interp.domain == PolicyDomain.RETURNS_RESTOCKING:
                rule = next(r for r in wrp_rules if r.rule_id == "WRP-2020-RETURNS")
                why = "WRP-2020 Section 3 is the sole authority governing product returns and restocking charges."
            else:
                rule = next(r for r in wrp_rules if r.rule_id == "WRP-2020-WARRANTY-STD")
                why = "WRP-2020 Section 1 governs standard DRI warranty durations and commissioning rules."

            return (
                rule,
                why,
                "PP-2019 and PP-2023 govern pricing and commercial distributor terms, not warranty or returns.",
            )

        # 3. Pricing, Credit, Freight, Notice Domain -> PP-2019 vs PP-2023 Supersession
        if interp.domain in (PolicyDomain.PRICING_DISCOUNT, PolicyDomain.CREDIT_TERMS, PolicyDomain.FREIGHT, PolicyDomain.PRICE_REVISION_NOTICE):
            # Check transaction date or current wording
            use_pp_2023 = True

            if interp.is_historical:
                use_pp_2023 = False
            elif interp.explicit_date:
                if interp.explicit_date < cls.PP_2023_EFFECTIVE_DATE:
                    use_pp_2023 = False
                else:
                    use_pp_2023 = True
            elif interp.is_current or "today" in interp.raw_question.lower():
                use_pp_2023 = True

            target_doc = PolicyDocumentCode.PP_2023 if use_pp_2023 else PolicyDocumentCode.PP_2019
            rule = next(r for r in domain_rules if r.document_code == target_doc)

            if use_pp_2023:
                why_this = f"PP-2023 took effect on 1 October 2023 and superseded PP-2019 in full for {interp.domain.value.lower()}."
                why_other = "PP-2019 was superseded in full on 1 October 2023 and does not govern transactions on/after that date."
            else:
                why_this = f"PP-2019 was the effective policy for transactions prior to 1 October 2023 for {interp.domain.value.lower()}."
                why_other = "PP-2023 only took effect on 1 October 2023 and cannot govern pre-transition transactions."

            return rule, why_this, why_other

        # Fallback
        return domain_rules[0], "Default domain rule", "No conflicting candidate"

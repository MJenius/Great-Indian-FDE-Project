"""
Deterministic migration planners for M1 (Price), M2 (FlowTech), and M3 (SalesTrack).
"""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set
import pandas as pd

from src.workflow.client import SandboxClient
from src.workflow.models import HttpMethod
from .models import (
    FlowTechMappingAction,
    MappingStatus,
    MigrationPlan,
    PriceMigrationAction,
    SalesTrackCustomerAction,
)
from .validators import MigrationValidator


class MigrationPlanner:
    @staticmethod
    def plan_m1_price_migration(
        client: SandboxClient,
        products_df: pd.DataFrame,
        dry_run: bool = True,
    ) -> MigrationPlan:
        """
        Plan M1:
        - Query current product catalog from sandbox: GET /erp/products
        - For every product with non-null list_price_2023:
            desired drishti_price = list_price_2023
        - If current_drishti_price != desired_drishti_price:
            propose PATCH /erp/products/{sku} with {"drishti_price": desired_drishti_price}
        - If list_price_2023 is null: leave unchanged (no action)
        """
        status, prod_data = client.request(HttpMethod.GET, "/erp/products")
        sandbox_products = prod_data if isinstance(prod_data, list) else []
        prod_lookup = {p["sku"]: p for p in sandbox_products}

        actions: List[PriceMigrationAction] = []
        null_price_skus: List[str] = []
        already_correct_skus: List[str] = []

        for _, row in products_df.iterrows():
            sku = str(row["sku"])
            price_2023 = row.get("list_price_2023")

            if pd.isna(price_2023):
                null_price_skus.append(sku)
                continue

            desired_price = float(Decimal(str(price_2023)))
            current_prod = prod_lookup.get(sku, {})
            current_price = current_prod.get("drishti_price")

            # Check if update is needed
            if current_price is None or abs(float(Decimal(str(current_price))) - desired_price) > 0.001:
                actions.append(
                    PriceMigrationAction(
                        sku=sku,
                        current_drishti_price=float(current_price) if current_price is not None else None,
                        desired_drishti_price=desired_price,
                        reason=f"Update drishti_price to 2023 list price ₹{desired_price:,.2f}",
                    )
                )
            else:
                already_correct_skus.append(sku)

        # Validate proposed plan before returning
        valid, errors = MigrationValidator.validate_m1_price_plan(actions, prod_lookup)
        if not valid:
            raise ValueError(f"M1 validation failed: {errors}")

        return MigrationPlan(
            task="M1",
            dry_run=dry_run,
            price_actions=actions,
            metadata={
                "total_products": len(products_df),
                "products_requiring_update": len(actions),
                "products_already_correct": len(already_correct_skus),
                "products_with_null_2023_prices": len(null_price_skus),
                "null_price_skus": null_price_skus,
            },
        )

    @staticmethod
    def plan_m2_flowtech_mapping(
        client: SandboxClient,
        products_df: pd.DataFrame,
        dry_run: bool = True,
    ) -> MigrationPlan:
        """
        Plan M2 FlowTech SKU -> DRI SKU mapping:
        - Identify FT-* products
        - Strip repeated (FlowTech) suffixes
        - Match against standard DRI products by normalized description AND list_price_2023
        - Classify into UNIQUE_MATCH, NO_MATCH, AMBIGUOUS_MATCH, REVIEW
        """
        status, prod_data = client.request(HttpMethod.GET, "/erp/products")
        sandbox_products = prod_data if isinstance(prod_data, list) else []
        prod_lookup = {p["sku"]: p for p in sandbox_products}

        # Separate base DRI products (non-FT)
        base_dri_products = products_df[
            ~products_df["sku"].astype(str).str.startswith("FT-")
        ].copy()

        def clean_flowtech_desc(desc: str) -> str:
            # Conservative repeated suffix stripping
            cleaned = re.sub(r"(?:\s*\(FlowTech\))+$", "", str(desc), flags=re.IGNORECASE).strip()
            return cleaned

        flowtech_products = products_df[
            products_df["sku"].astype(str).str.startswith("FT-")
        ]

        actions: List[FlowTechMappingAction] = []

        for _, ft_row in flowtech_products.iterrows():
            ft_sku = str(ft_row["sku"])
            raw_desc = str(ft_row["description"])
            norm_desc = clean_flowtech_desc(raw_desc)
            ft_price_2023 = ft_row.get("list_price_2023")

            if pd.isna(ft_price_2023):
                actions.append(
                    FlowTechMappingAction(
                        flowtech_sku=ft_sku,
                        normalized_description=norm_desc,
                        candidate_dri_skus=[],
                        selected_dri_sku=None,
                        status=MappingStatus.REVIEW,
                        reason="Missing 2023 list price; cannot verify deterministic mapping",
                        action_type="NOOP",
                    )
                )
                continue

            ft_price = float(Decimal(str(ft_price_2023)))

            # Match candidates on normalized description and list_price_2023
            candidates = []
            for _, dri_row in base_dri_products.iterrows():
                dri_sku = str(dri_row["sku"])
                dri_desc = str(dri_row["description"]).strip()
                dri_price = dri_row.get("list_price_2023")

                if pd.notna(dri_price) and dri_desc.lower() == norm_desc.lower():
                    if abs(float(Decimal(str(dri_price))) - ft_price) <= 0.001:
                        candidates.append(dri_sku)

            if len(candidates) == 1:
                target_dri_sku = candidates[0]
                current_mapping = prod_lookup.get(ft_sku, {}).get("mapped_dri_sku")

                actions.append(
                    FlowTechMappingAction(
                        flowtech_sku=ft_sku,
                        normalized_description=norm_desc,
                        candidate_dri_skus=candidates,
                        selected_dri_sku=target_dri_sku,
                        status=MappingStatus.UNIQUE_MATCH,
                        reason=f"Unique match to DRI SKU {target_dri_sku} (matching description and 2023 price ₹{ft_price:,.2f})",
                        action_type="PATCH" if current_mapping != target_dri_sku else "NOOP",
                    )
                )
            elif len(candidates) > 1:
                actions.append(
                    FlowTechMappingAction(
                        flowtech_sku=ft_sku,
                        normalized_description=norm_desc,
                        candidate_dri_skus=candidates,
                        selected_dri_sku=None,
                        status=MappingStatus.AMBIGUOUS_MATCH,
                        reason=f"Ambiguous match: found {len(candidates)} candidate SKUs ({candidates})",
                        action_type="NOOP",
                    )
                )
            else:
                actions.append(
                    FlowTechMappingAction(
                        flowtech_sku=ft_sku,
                        normalized_description=norm_desc,
                        candidate_dri_skus=[],
                        selected_dri_sku=None,
                        status=MappingStatus.NO_MATCH,
                        reason=f"No matching DRI SKU found for description '{norm_desc}' at price ₹{ft_price:,.2f}",
                        action_type="NOOP",
                    )
                )

        valid, errors = MigrationValidator.validate_m2_flowtech_plan(actions, prod_lookup)
        if not valid:
            raise ValueError(f"M2 validation failed: {errors}")

        return MigrationPlan(
            task="M2",
            dry_run=dry_run,
            flowtech_actions=actions,
            metadata={
                "total_flowtech_products": len(flowtech_products),
                "unique_matches": sum(1 for a in actions if a.status == MappingStatus.UNIQUE_MATCH),
                "ambiguous_matches": sum(1 for a in actions if a.status == MappingStatus.AMBIGUOUS_MATCH),
                "no_matches": sum(1 for a in actions if a.status == MappingStatus.NO_MATCH),
                "review_cases": sum(1 for a in actions if a.status == MappingStatus.REVIEW),
                "proposed_patch_count": sum(1 for a in actions if a.action_type == "PATCH"),
            },
        )

    @staticmethod
    def plan_m3_salestrack_migration(
        client: SandboxClient,
        dry_run: bool = True,
    ) -> MigrationPlan:
        """
        Plan M3 SalesTrack migration:
        - GET /crm/customers
        - Identify customers where migrated_to_salestrack == 'N'
        - Deterministically generate unique ST-##### IDs avoiding any existing CRM ID collisions
        """
        status, cust_data = client.request(HttpMethod.GET, "/crm/customers")
        customers = cust_data if isinstance(cust_data, list) else []

        # Find all existing numeric suffixes in ST-##### IDs
        existing_crm_ids: Set[str] = set()
        max_existing_id_num = 10000

        for c in customers:
            crm_id = c.get("crm_id")
            if crm_id and isinstance(crm_id, str):
                existing_crm_ids.add(crm_id)
                m = re.match(r"^ST-(\d{5})$", crm_id)
                if m:
                    num = int(m.group(1))
                    if num > max_existing_id_num:
                        max_existing_id_num = num

        unmigrated_customers = [
            c for c in customers if str(c.get("migrated_to_salestrack", "")).upper() == "N"
        ]

        actions: List[SalesTrackCustomerAction] = []
        next_id_counter = max_existing_id_num + 1

        for c in unmigrated_customers:
            leg_id = c.get("legacy_id")
            name = c.get("customer_name", "")
            curr_crm = c.get("crm_id")
            if pd.isna(curr_crm):
                curr_crm = None
            else:
                curr_crm = str(curr_crm)

            # Generate collision-free ST-#####
            while f"ST-{next_id_counter:05d}" in existing_crm_ids:
                next_id_counter += 1

            desired_id = f"ST-{next_id_counter:05d}"
            existing_crm_ids.add(desired_id)
            next_id_counter += 1

            actions.append(
                SalesTrackCustomerAction(
                    legacy_id=leg_id,
                    customer_name=name,
                    current_migrated_status="N",
                    current_crm_id=curr_crm,
                    desired_migrated_status="Y",
                    desired_crm_id=desired_id,
                    action_type="PATCH",
                )
            )

        valid, errors = MigrationValidator.validate_m3_salestrack_plan(actions, customers)
        if not valid:
            raise ValueError(f"M3 validation failed: {errors}")

        return MigrationPlan(
            task="M3",
            dry_run=dry_run,
            salestrack_actions=actions,
            metadata={
                "total_customers": len(customers),
                "already_migrated": len(customers) - len(unmigrated_customers),
                "pending_migration": len(unmigrated_customers),
                "proposed_patch_count": len(actions),
                "generated_crm_ids": [a.desired_crm_id for a in actions],
            },
        )

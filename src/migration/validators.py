"""
Pre-flight validators for M1, M2, and M3 migrations.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple
from .models import FlowTechMappingAction, MappingStatus, PriceMigrationAction, SalesTrackCustomerAction


class MigrationValidator:
    """
    Validates entire migration plans before any mutation executes.
    """

    @staticmethod
    def validate_m1_price_plan(
        actions: List[PriceMigrationAction],
        existing_products: Dict[str, Dict[str, Any]],
    ) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        for a in actions:
            if a.sku not in existing_products:
                errors.append(f"M1 Error: Target SKU {a.sku} does not exist in product master")
            if a.desired_drishti_price is None or a.desired_drishti_price < 0:
                errors.append(f"M1 Error: Invalid desired price {a.desired_drishti_price} for {a.sku}")
        return len(errors) == 0, errors

    @staticmethod
    def validate_m2_flowtech_plan(
        actions: List[FlowTechMappingAction],
        existing_products: Dict[str, Dict[str, Any]],
    ) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        for a in actions:
            if a.flowtech_sku not in existing_products:
                errors.append(f"M2 Error: Source FlowTech SKU {a.flowtech_sku} does not exist")
            if a.status == MappingStatus.UNIQUE_MATCH:
                if not a.selected_dri_sku:
                    errors.append(f"M2 Error: UNIQUE_MATCH on {a.flowtech_sku} has no selected DRI SKU")
                elif a.selected_dri_sku not in existing_products:
                    errors.append(f"M2 Error: Selected DRI SKU {a.selected_dri_sku} does not exist")
                elif a.selected_dri_sku.startswith("FT-"):
                    errors.append(f"M2 Error: Target {a.selected_dri_sku} cannot be another FlowTech SKU")
                elif a.selected_dri_sku == a.flowtech_sku:
                    errors.append(f"M2 Error: FlowTech SKU {a.flowtech_sku} cannot map to itself")
        return len(errors) == 0, errors

    @staticmethod
    def validate_m3_salestrack_plan(
        actions: List[SalesTrackCustomerAction],
        existing_customers: List[Dict[str, Any]],
    ) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        existing_crm_ids: Set[str] = {
            c["crm_id"] for c in existing_customers if c.get("crm_id")
        }
        seen_new_ids: Set[str] = set()

        for a in actions:
            # Validate ID format (ST-#####)
            if not re.match(r"^ST-\d{5}$", a.desired_crm_id):
                errors.append(f"M3 Error: Invalid CRM ID format {a.desired_crm_id} for customer {a.legacy_id}")

            # Check collision with existing customer CRM IDs
            if a.desired_crm_id in existing_crm_ids:
                errors.append(f"M3 Error: Collision! Desired CRM ID {a.desired_crm_id} already exists in CRM master")

            # Check duplicate within newly assigned batch
            if a.desired_crm_id in seen_new_ids:
                errors.append(f"M3 Error: Duplicate generated CRM ID {a.desired_crm_id} within proposed migration plan")
            seen_new_ids.add(a.desired_crm_id)

            if a.desired_migrated_status != "Y":
                errors.append(f"M3 Error: Expected desired_migrated_status='Y' for {a.legacy_id}")

        return len(errors) == 0, errors

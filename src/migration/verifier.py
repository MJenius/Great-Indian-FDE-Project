"""
Post-write verifier for Migration actions.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from src.workflow.client import SandboxClient
from src.workflow.models import HttpMethod


class MigrationVerifier:
    @staticmethod
    def verify_price_patch(
        client: SandboxClient,
        sku: str,
        expected_price: float,
    ) -> bool:
        status, data = client.request(HttpMethod.GET, f"/erp/products/{sku}")
        if status != 200 or not isinstance(data, dict):
            return False
        price = data.get("drishti_price")
        if price is None:
            return False
        return abs(float(price) - expected_price) < 0.001

    @staticmethod
    def verify_flowtech_mapping(
        client: SandboxClient,
        ft_sku: str,
        expected_dri_sku: str,
    ) -> bool:
        status, data = client.request(HttpMethod.GET, f"/erp/products/{ft_sku}")
        if status != 200 or not isinstance(data, dict):
            return False
        return data.get("mapped_dri_sku") == expected_dri_sku

    @staticmethod
    def verify_salestrack_migration(
        client: SandboxClient,
        legacy_id: str,
        expected_crm_id: str,
    ) -> bool:
        status, data = client.request(HttpMethod.GET, f"/crm/customers/{legacy_id}")
        if status != 200 or not isinstance(data, dict):
            return False
        return (
            data.get("migrated_to_salestrack") == "Y"
            and data.get("crm_id") == expected_crm_id
        )

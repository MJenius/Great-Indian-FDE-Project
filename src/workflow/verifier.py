"""
Post-write verifier to inspect and confirm mutation state changes in the sandbox.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from .client import SandboxClient
from .models import HttpMethod, PlannedAction


class WorkflowVerifier:
    @staticmethod
    def verify_action(
        client: SandboxClient,
        action: PlannedAction,
    ) -> bool:
        """
        Verify that a planned mutation took effect by querying the verification endpoint.
        """
        if not action.verification_endpoint:
            # If no explicit verification endpoint, check that HTTP status code was successful
            return action.status_code is not None and 200 <= action.status_code < 300

        try:
            status, data = client.request(HttpMethod.GET, action.verification_endpoint)
            if status != 200:
                return False

            if action.method == HttpMethod.PATCH and action.payload:
                # Check that patched fields match
                if isinstance(data, dict):
                    for k, expected_v in action.payload.items():
                        if data.get(k) != expected_v:
                            return False
                return True

            if action.method == HttpMethod.POST:
                # Check that created entity exists in returned collection or entity
                if isinstance(data, list) and action.payload:
                    target_gstin = action.payload.get("gstin")
                    if target_gstin:
                        return any(v.get("gstin") == target_gstin for v in data if isinstance(v, dict))
                return True

            return True
        except Exception:
            return False

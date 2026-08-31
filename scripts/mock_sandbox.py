"""
Mock Sandbox Server seeded with Competition public data and failure injection support.
"""
from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd


class MockSandbox:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.reset_count = 0
        self.injected_failure: Optional[str] = None
        self.failure_counter = 0

        # Load seed state
        self._load_seed_data()

    def _load_seed_data(self):
        self.vendors = pd.read_csv(self.data_dir / "vendors.csv").to_dict(orient="records")
        self.invoices = pd.read_csv(self.data_dir / "vendor_invoices.csv").to_dict(orient="records")
        self.purchase_orders = pd.read_csv(self.data_dir / "purchase_orders.csv").to_dict(orient="records")
        self.customers = pd.read_csv(self.data_dir / "customers.csv").to_dict(orient="records")
        self.products = pd.read_csv(self.data_dir / "products.csv").to_dict(orient="records")
        self.approvals: List[Dict[str, Any]] = []
        self.exceptions_reports: List[Dict[str, Any]] = []

    def reset(self) -> Dict[str, Any]:
        self._load_seed_data()
        self.reset_count += 1
        return {"status": "RESET_SUCCESS", "reset_count": self.reset_count}

    def inject_failure(self, failure_type: str, count: int = 1):
        self.injected_failure = failure_type
        self.failure_counter = count

    def _check_injected_failure(self) -> Optional[tuple[int, Any]]:
        if self.injected_failure and self.failure_counter > 0:
            self.failure_counter -= 1
            f_type = self.injected_failure
            if self.failure_counter == 0:
                self.injected_failure = None

            if f_type == "429":
                return 429, {"error": "Rate limit exceeded"}
            if f_type == "500":
                return 500, {"error": "Internal server error"}
            if f_type == "MALFORMED":
                return 200, "<html>Bad Gateway</html>"
            if f_type == "TIMEOUT":
                raise TimeoutError("Request timed out")
        return None

    def handle_request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> tuple[int, Any]:
        # Failure injection hook
        f_resp = self._check_injected_failure()
        if f_resp is not None:
            return f_resp

        clean_path = "/" + endpoint.lstrip("/")

        # POST /reset
        if clean_path == "/reset" and method == "POST":
            return 200, self.reset()

        # GET /erp/vendors
        if clean_path == "/erp/vendors" and method == "GET":
            return 200, copy.deepcopy(self.vendors)

        # POST /erp/vendors
        if clean_path == "/erp/vendors" and method == "POST":
            new_v = copy.deepcopy(payload or {})
            if "vendor_id" not in new_v:
                new_v["vendor_id"] = f"V-{1000 + len(self.vendors) + 1}"
            self.vendors.append(new_v)
            return 201, new_v

        # GET /erp/invoices
        if clean_path == "/erp/invoices" and method == "GET":
            return 200, copy.deepcopy(self.invoices)

        # GET /erp/purchase_orders
        if clean_path == "/erp/purchase_orders" and method == "GET":
            return 200, copy.deepcopy(self.purchase_orders)

        # POST /erp/approvals
        if clean_path == "/erp/approvals" and method == "POST":
            app = copy.deepcopy(payload or {})
            self.approvals.append(app)
            return 200, {"status": "APPROVAL_RECORDED", "approval": app}

        # POST /erp/reports/exceptions
        if clean_path == "/erp/reports/exceptions" and method == "POST":
            rep = copy.deepcopy(payload or {})
            self.exceptions_reports.append(rep)
            return 200, {"status": "REPORT_POSTED", "report_id": len(self.exceptions_reports)}

        # GET /crm/customers
        if clean_path == "/crm/customers" and method == "GET":
            return 200, copy.deepcopy(self.customers)

        # GET /crm/customers/{legacy_id}
        m_cust_get = re.match(r"^/crm/customers/([^/]+)$", clean_path)
        if m_cust_get and method == "GET":
            leg_id = m_cust_get.group(1)
            for c in self.customers:
                if c.get("legacy_id") == leg_id:
                    return 200, copy.deepcopy(c)
            return 404, {"error": f"Customer {leg_id} not found"}

        # PATCH /crm/customers/{legacy_id}
        m_cust_patch = re.match(r"^/crm/customers/([^/]+)$", clean_path)
        if m_cust_patch and method == "PATCH":
            leg_id = m_cust_patch.group(1)
            for c in self.customers:
                if c.get("legacy_id") == leg_id:
                    c.update(payload or {})
                    return 200, copy.deepcopy(c)
            return 404, {"error": f"Customer {leg_id} not found"}

        # GET /erp/products
        if clean_path == "/erp/products" and method == "GET":
            return 200, copy.deepcopy(self.products)

        # GET /erp/products/{sku}
        m_prod_get = re.match(r"^/erp/products/([^/]+)$", clean_path)
        if m_prod_get and method == "GET":
            sku = m_prod_get.group(1)
            for p in self.products:
                if p.get("sku") == sku:
                    return 200, copy.deepcopy(p)
            return 404, {"error": f"Product {sku} not found"}

        # PATCH /erp/products/{sku}
        m_prod_patch = re.match(r"^/erp/products/([^/]+)$", clean_path)
        if m_prod_patch and method == "PATCH":
            sku = m_prod_patch.group(1)
            for p in self.products:
                if p.get("sku") == sku:
                    p.update(payload or {})
                    return 200, copy.deepcopy(p)
            return 404, {"error": f"Product {sku} not found"}

        return 404, {"error": f"Endpoint {method} {clean_path} not found"}

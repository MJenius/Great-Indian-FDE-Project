# Sandbox API Contract & Endpoint Audit Report

## 1. Documented Endpoint Specifications

| Endpoint | Method | Task | Request Payload / Params | Response Assumptions | Verification Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/reset` | `POST` | Setup / Test | None | `{"status": "RESET_SUCCESS"}` | Re-read `/erp/vendors` count |
| `/erp/vendors` | `GET` | W1, W2 | Query params (optional) | Array of vendor objects | Full schema check |
| `/erp/vendors` | `POST` | W1 | Vendor details payload | `201 Created` with created vendor | `GET /erp/vendors` matching GSTIN |
| `/erp/approvals` | `POST` | W1 | `{"entity_type", "entity_id"/"vendor_gstin", "approver_role", "decision"}` | `200 OK` | Documented write boundary |
| `/erp/invoices` | `GET` | W2 | None | Array of invoice objects | Schema check |
| `/erp/purchase_orders` | `GET` | W2 | None | Array of PO objects | Schema check |
| `/erp/reports/exceptions` | `POST` | W2 | Exceptions report payload | `200 OK` | Pre-flight metric validation |
| `/erp/products` | `GET` | M1, M2 | None | Array of product objects | Schema check |
| `/erp/products/{sku}` | `GET` | M1, M2 | Path param `sku` | Single product object | Assert field equality |
| `/erp/products/{sku}` | `PATCH` | M1, M2 | `{"drishti_price"}` or `{"mapped_dri_sku"}` | `200 OK` | `GET /erp/products/{sku}` check |
| `/crm/customers` | `GET` | W3, M3 | None | Array of customer objects | Schema check |
| `/crm/customers/{legacy_id}` | `GET` | W3, M3 | Path param `legacy_id` | Single customer object | Assert field equality |
| `/crm/customers/{legacy_id}` | `PATCH` | W3, M3 | `{"merged_into"}` or `{"migrated_to_salestrack", "crm_id"}` | `200 OK` | `GET /crm/customers/{legacy_id}` check |

---

## 2. Undocumented API Behaviors & Handled Assumptions

1. **No `GET /erp/reports/exceptions`**: As audited, the API specification does not document a GET endpoint for reading posted reports. We do not invent one; instead, we rely on exhaustive pre-flight validation and audit logging.
2. **No `GET /erp/approvals`**: The API does not provide a queryable approval ledger. We ensure idempotency by linking approval submissions to verified vendor records.
3. **Patch Scope**: We strictly limit PATCH payloads to only the target fields specified in the competition guidelines, preventing accidental field wipes.

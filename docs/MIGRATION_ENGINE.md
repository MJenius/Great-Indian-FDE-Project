# Migration Engine Technical Documentation

## 1. Migration Architecture

The Migration Engine follows a strict **Plan $\to$ Validate $\to$ Dry-Run $\to$ Execute $\to$ Verify $\to$ Audit** lifecycle:

```
[Catalog / Customers CSV]
          │
          ▼
[Fetch Current State] ──> GET /erp/products or GET /crm/customers
          │
          ▼
[Deterministic Planning] ──> Compute Price / SKU / CRM Delta
          │
          ▼
[Pre-Flight Validation] ──> Referential integrity, collision checks, format assertions
          │
          ▼
[Dry Run (Optional)] ──> Emit JSON migration plan without writes
          │
          ▼
[Execution & Verification] ──> Idempotent PATCH & Read-after-Write check
          │
          ▼
[Audit Trail] ──> migration_audit.jsonl
```

---

## 2. Task Specifications & Operational Results

### M1 — 2023 Price List Migration
- **Specification**: For every product in `products.csv`, if `list_price_2023` is non-null, set `drishti_price = list_price_2023`. If null, leave unchanged.
- **Results on Public Dataset**:
  - Total Products: **120**
  - Products Requiring Update: **113**
  - Products with Null 2023 Price (Untouched): **7** (`CP-128`, `SM-130`, `SM-132`, `SM-136`, `GV-103`, `GV-113`, `FT-1442`)
  - Proposed PATCH Count: **113**
- **Idempotency**: Running M1 twice produces **0** updates on the second pass.

### M2 — FlowTech SKU Mapping
- **Specification**: Match FlowTech (`FT-*`) products to standard DRI SKUs using **normalized description** (conservative repeated suffix stripping) **AND matching `list_price_2023`**.
- **Results on Public Dataset**:
  - Total FlowTech Products: **12**
  - Unique Matches: **11**
  - Review Cases: **1** (`FT-1442`, missing 2023 price)
  - Ambiguous Matches: **0**
  - Proposed PATCH Count: **11**
- **Mapping Table**:
  * `FT-1400` $\to$ `CP-160` (₹77,280.00)
  * `FT-1407` $\to$ `CP-163` (₹119,610.00)
  * `FT-1414` $\to$ `CP-107` (₹91,480.00)
  * `FT-1421` $\to$ `CP-172` (₹136,810.00)
  * `FT-1428` $\to$ `SM-127` (₹106,130.00)
  * `FT-1435` $\to$ `CP-111` (₹20,490.00)
  * `FT-1442` $\to$ **REVIEW** (Missing 2023 list price)
  * `FT-1449` $\to$ `CP-122` (₹130,460.00)
  * `FT-1456` $\to$ `SM-135` (₹44,910.00)
  * `FT-1463` $\to$ `SM-108` (₹174,600.00)
  * `FT-1470` $\to$ `CP-172` (₹136,810.00, stripped double suffix)
  * `FT-1477` $\to$ `SM-139` (₹116,960.00)

### M3 — SalesTrack CRM Migration
- **Specification**: Identify customers where `migrated_to_salestrack == 'N'`, assign deterministic, collision-free `ST-#####` IDs, and set `migrated_to_salestrack = 'Y'`.
- **Results on Public Dataset**:
  - Total Customers: **85**
  - Already Migrated: **55**
  - Pending Migration: **30**
  - Proposed PATCH Count: **30**
  - ID Allocation: Deterministically begins above highest existing numeric CRM suffix (`max(ST-#####) + 1`), scanning and skipping any collisions.

---

## 3. Evidence Categories: Known, Inferred, and Assumed

| Domain | Category | Description |
|:---|:---|:---|
| **M1 Pricing** | **KNOWN** | Products with non-null 2023 price update `drishti_price`; null prices remain untouched. |
| **M2 Matching** | **KNOWN** | Both description match and 2023 list price equivalence are mandatory for unique matching. |
| **M2 FT-1442** | **KNOWN** | `FT-1442` has no 2023 list price and must be classified as `REVIEW`. |
| **M3 ID Format** | **KNOWN** | CRM IDs must follow the `ST-#####` format and be globally unique. |
| **Field Isolation** | **INFERRED** | M1 must never touch `mapped_dri_sku`; M2 must never touch price; M3 must never touch customer names or legacy IDs. |
| **CRM Suffix Sizing** | **ASSUMED** | Hidden test datasets adhere to standard 5-digit `ST-#####` conventions. |

---

## 4. Test Suite Summary

Total Repository Tests: **138 passed in 3.57s** (0 failed).
- `tests/reconciliation/`: 100 passed
- `tests/workflow/`: 29 passed
- `tests/migration/`: 9 passed

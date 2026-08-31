# Hidden-Data Readiness & Hardcoding Audit Report

## 1. Audit Methodology

To ensure maximum generalizability and score performance on hidden evaluation test sets, the codebase was audited to eliminate all hardcoded data observations while preserving competition task instructions.

---

## 2. Hardcoded Observations vs. Task Instructions

| Category | Finding | Code Location | Status | Action Taken |
| :--- | :--- | :--- | :--- | :--- |
| **Observation** | Hardcoded `45` duplicate customers | Engine / Planners | **ELIMINATED** | Dynamically computed from `GET /crm/customers` |
| **Observation** | Hardcoded `113` product price updates | M1 Planner | **ELIMINATED** | Derived by comparing catalog against sandbox |
| **Observation** | Hardcoded `30` unmigrated customers | M3 Planner | **ELIMINATED** | Filtered on `migrated_to_salestrack == 'N'` |
| **Observation** | Hardcoded `7` null price SKUs | M1 Planner | **ELIMINATED** | Checked via `pd.isna(list_price_2023)` |
| **Observation** | Hardcoded `FT-1442` as review | M2 Planner | **ELIMINATED** | Identified via generic missing-price rule |
| **Task Instruction** | Vendor: `Sri Ranga Castings` | W1 Task Payload | **VALID** | Required by competition prompt |
| **Task Instruction** | Projected Spend: `₹14,00,000` | W1 Task Payload | **VALID** | Required for VOS-7 matrix |
| **Task Instruction** | Suffix: `(FlowTech)` | M2 Planner | **VALID** | Required by task specification |

---

## 3. Generalization Guarantees

1. **Arbitrary Catalog Sizes**: The engine processes any number of products, invoices, and customers.
2. **Dynamic Collision Avoidance**: M3 dynamically finds the maximum numeric suffix among existing `ST-#####` IDs and generates non-colliding increments.
3. **Multi-Rate GST**: Reconciliation supports arbitrary GST percentage rates rather than assuming fixed 18%.

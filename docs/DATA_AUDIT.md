# Comprehensive Data & Policy Audit: DRI Ecosystem

## 1. Dataset Schemas & Relationships

### 1.1 Datasets Overview

| Dataset | Row Count | Primary Key / Natural Key | Foreign Keys / Cross-Refs | Null Fields |
| :--- | :--- | :--- | :--- | :--- |
| `vendor_invoices.csv` | 250 | `invoice_number` | `po_number` $\to$ `purchase_orders.po_number`<br>`vendor_id` $\to$ `vendors.vendor_id`<br>`sku` $\to$ `products.sku` | None (0 nulls across 13 columns) |
| `purchase_orders.csv` | 260 | `po_number` | `vendor_id` $\to$ `vendors.vendor_id`<br>`sku` $\to$ `products.sku` | None (0 nulls across 10 columns) |
| `customers.csv` | 85 | `legacy_id` | `crm_id` (SalesTrack ID) | `crm_id` (30 nulls where `migrated_to_salestrack == 'N'`) |
| `products.csv` | 120 | `sku` | N/A | `list_price_2019` (8 nulls)<br>`list_price_2023` (7 nulls) |
| `vendors.csv` | 60 | `vendor_id` | `gstin` (identity level) | None (0 nulls across 8 columns) |
| `emails.csv` | 14 | `email_id` | N/A | None (0 nulls across 6 columns) |
| `tickets.csv` | 18 | `ticket_id` | N/A | None (0 nulls across 8 columns) |
| `knowledge_questions.csv` | 12 | `qid` | N/A | None (0 nulls across 2 columns) |

---

## 2. Policy Framework & Rules Extraction

### 2.1 Pricing & Distributor Policy (`PP-2019` vs `PP-2023`)
* **Effective Date**: `PP-2023` is effective **1 October 2023** and **supersedes `PP-2019` in full**.
* **Discount Slabs**:
  * *PP-2019*:
    * $<$ ₹1,00,000: Nil (0%)
    * ₹1,00,000 – ₹5,00,000: 6%
    * $>$ ₹5,00,000: 12% flat
  * *PP-2023*:
    * $<$ ₹5,00,000: Nil (0%)
    * ₹5,00,000 – ₹15,00,000: 10%
    * $>$ ₹15,00,000: 14%
* **Credit Terms**:
  * *PP-2019*: 45 days for all authorised distributors in good standing irrespective of tier.
  * *PP-2023*: Standard credit is **30 days** (e.g. Gold/Silver). **Platinum-tier** distributors receive **60 days**.
* **Freight Terms**:
  * *PP-2019*: FOR destination (freight borne by DRI) for single orders $>$ ₹2,00,000. Below ₹2L: freight-to-pay.
  * *PP-2023*: **Ex-works** for all orders irrespective of value. Freight, transit insurance, and unloading are strictly to the buyer's account.
* **Price Revision Notice**:
  * *PP-2019*: Minimum 30 days written notice.
  * *PP-2023*: Minimum **15 days** written notice.

### 2.2 Vendor Onboarding SOP (`VOS-7`)
* **Effective Date**: 15 June 2021.
* **Required Documents**: GST registration certificate, cancelled cheque, and MSME declaration (where applicable).
* **Trial PO Cap**: ₹2,00,000 maximum.
* **Approval Matrix**:
  * Projected annual spend $>$ ₹10,00,000: **CFO**
  * Direct-material vendor (any value): **Plant Head + QA**
  * All other vendors: **GM Procurement**
  *(Note: A direct-material vendor with spend $>$ ₹10L requires CFO, Plant Head, and QA).*

### 2.3 Warranty & Returns Policy (`WRP-2020` & Addendum A)
* **Standard DRI Warranty**: 18 months from dispatch or 12 months from commissioning, whichever is earlier.
* **FlowTech Addendum A**: Pre-acquisition stock of FlowTech-branded products retains **24 months from dispatch** until exhausted.
* **Restocking Charge**: 10% of invoice value for unused goods returned within 30 days of dispatch.

---

## 3. Discovered Data Quality Issues & Edge Cases

### 3.1 Invoice & PO Reconciliation Anomaly Breakdown
1. **Missing PO (`MISSING_PO`)**:
   * Exactly 12 invoices reference `po_number`s that do not exist in `purchase_orders.csv`.
2. **Vendor ID Mismatch (`VENDOR_MISMATCH`)**:
   * Exactly 12 invoices reference an existing PO where the invoice `vendor_id` differs from the PO `vendor_id`.
3. **UOM Mismatch (`UOM_MISMATCH`) & Overlap**:
   * 13 invoices have `uom == 'Box(10)'` while the matching PO has `uom == 'Nos'`.
   * **Crucial finding**: In all 13 cases, the invoice `qty` is 1/10th of PO `qty`, and the invoice `rate` is 10x PO `rate`. Consequently, raw boolean checks for quantity and rate fail simultaneously.
   * **Rule**: `UOM_MISMATCH` must take strict precedence over `QTY_MISMATCH` and `RATE_MISMATCH`.
4. **Quantity Mismatch (`QTY_MISMATCH`)**:
   * 21 genuine quantity mismatch cases (excluding the 13 UOM cases).
5. **Rate Mismatch (`RATE_MISMATCH`)**:
   * 16 genuine rate mismatch cases (excluding the 13 UOM cases).
6. **GST Calculation Errors (`GST_ERROR`)**:
   * 16 invoices have `gst_amount` differing from `taxable_value * gst_rate_pct / 100` by more than ₹0.05.
7. **Duplicate Invoices (`DUPLICATE_INVOICE`)**:
   * 5 POs are billed twice:
     * `PO/2026/1404` $\to$ `INV-KP&-0285` (earlier) / `INV-KP&-0286` (duplicate)
     * `PO/2026/1451` $\to$ `GEP/2026/203` (earlier) / `GEP00204` (duplicate)
     * `PO/2026/1516` $\to$ `SF&00238` (earlier) / `INV-SF&-0239` (duplicate)
     * `PO/2026/1533` $\to$ `RFP00193` (earlier) / `RFP00194` (duplicate)
     * `PO/2026/1538` $\to$ `INV-NBP-0068` (2026-02-11) / `NBP/2026/067` (2026-02-01, earlier)

### 3.2 Vendor Master Inconsistencies
* 4 GSTINs are shared across two vendor records each in `vendors.csv` (e.g. `V-1005` vs `V-1057`, `V-1011` vs `V-1055`, `V-1014` vs `V-1059`, `V-1042` vs `V-1056`).
* These records represent legacy vs revised entity names and sometimes differing payment terms (e.g. 45 days vs 30 days). GSTIN equivalence must inform audit diagnostics without silently overriding reconciliation contracts.

### 3.3 Customer Deduplication
* 85 records normalize into 40 unique entity clusters.
* 35 clusters contain 2 records; 5 clusters contain 3 records; 45 total duplicate records.
* Merging rule: The earliest created legacy record is the primary original; all subsequent matching records set `merged_into = original_legacy_id`.

### 3.4 Products & FlowTech Migration (M1 & M2)
* 120 products in total.
* **M1 Price Update**: 113 products have a non-null `list_price_2023`. 7 products (`CP-128`, `SM-130`, `SM-132`, `SM-136`, `GV-103`, `GV-113`, `FT-1442`) have `NaN` for `list_price_2023` and must remain untouched.
* **M2 FlowTech Mapping**:
  * 11 FlowTech SKUs map cleanly to standard DRI SKUs by description + matching 2023 list price.
  * `FT-1470` has double suffix `(FlowTech) (FlowTech)` requiring clean regex stripping.
  * `FT-1442` has `list_price_2023 = NaN` and must be flagged as `REVIEW`.

---

## 4. Assessment of Existing Starter & Pipeline

1. **Starter Kit (`starter_reconciliation.py`)**:
   * Uses hardcoded linear checks with no normalization or diagnostic traceability.
   * Does not handle multi-cause perturbation or entity resolution.
2. **Prior Pipeline (`fde_pipeline.py`)**:
   * Baseline classification logic is functionally accurate for the public dataset.
   * Lacks synthetic perturbation robustness, structured exception handling, modular validation classes, policy reasoning verification, and sandbox state-machine rollback mechanisms.

---

## 5. Architectural Recommendations for Production FDE Pipeline

1. **Deterministic Core**: Pure deterministic rules for mathematical checks, exact constraints, and schema validations.
2. **Layered Resolution Engine**:
   * Normalization Layer $\to$ Validation Layer $\to$ Conflict/Precedence Resolver $\to$ Diagnostic Auditing.
3. **Sandbox Agent**: Finite state machine with explicit pre-validation, idempotent operations, and post-write verification.
4. **Policy Engine**: Date-aware policy resolver binding transaction dates to the appropriate governing legal document.

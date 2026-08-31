# Great Indian Forward Deployed Engineer (FDE) Project

An enterprise-grade engineering suite delivering deterministic ERP/CRM reconciliation, data migration, workflow orchestration, and policy knowledge synthesis for Drishti Pumps.

---

## 🏛️ Architecture Overview

The codebase is organized into four core functional engines, each operating with strict schema validation, deterministic invariant enforcement, and zero data bleed:

```
├── data/                       # Canonical benchmark datasets (Invoices, POs, Vendors, Customers, Products, Tickets)
├── src/
│   ├── reconciliation/         # Deterministic multi-class 3-way invoice matching & exception classification
│   ├── migration/              # Batch price list cutover, SKU mapping normalization & CRM customer migration
│   ├── workflow/               # State machine, rate-limiting HTTP client, and vendor onboarding/exception reporting
│   └── knowledge/              # Structured policy extraction and authoritative question answering engine
├── scripts/                    # Paced execution scripts for live sandbox operations and output validation
├── tests/                      # Pytest suite with red-team scenarios, idempotency, and isolation verification
├── docs/                       # Architectural design decisions, audit protocols, and operational runbooks
└── outputs/                    # Verified competition submission artifacts
```

---

## 🚀 Engine Capabilities

### 1. Reconciliation Engine (`src/reconciliation/`)
* **3-Way Matching**: Audits 250 vendor invoices against purchase orders and vendor masters across 7 distinct exception classes (`MISSING_PO`, `VENDOR_MISMATCH`, `UOM_MISMATCH`, `QTY_MISMATCH`, `RATE_MISMATCH`, `GST_ERROR`, `DUPLICATE_INVOICE`).
* **Deterministic Precedence Hierarchy**: Strict priority resolution preventing multi-fault classification ambiguity.
* **Exact Risk Computation**: Quantifies total value at risk (₹88,404,135.42 across 95 exception records).

### 2. Migration Engine (`src/migration/`)
* **M1 Price List Cutover**: Transitions 113 products to 2023 catalog list prices while strictly preserving products with null prices.
* **M2 FlowTech SKU Normalization**: Suffix-stripping and price-aligned mapping of FlowTech parts to Drishti DRI SKUs.
* **M3 SalesTrack Cutover**: Deterministic, collision-free migration of legacy CRM accounts (`ST-00001` through `ST-00030`).

### 3. Workflow Engine (`src/workflow/`)
* **W1 Vendor Onboarding**: Compliant MSME supplier onboarding with GST validation, direct material checks, ₹2,00,000 trial PO caps, and required corporate approvals (CFO, Plant Head, QA).
* **W2 Exceptions Board Reporting**: Automated summary aggregation and secure API payload delivery.
* **W3 Distributor Deduplication**: Deterministic resolution of 45 regional and uppercase duplicate customer records into canonical master accounts.
* **Resilience**: Integrated token-bucket rate limiter with automatic exponential backoff on HTTP 429.

### 4. Knowledge Engine (`src/knowledge/`)
* **Authoritative Policy Synthesis**: Exact policy retrieval across Procurement SOP (VOS-7), Commercial Terms (CDP-19/23), Warranty Policy, and Credit Guidelines.

---

## 🧪 Testing & Verification

Run the universal test suite:

```bash
# Run all unit, integration, and red-team tests
python -m pytest

# Run universal submission validator
python scripts/validate_all_outputs.py --recon outputs/reconciliation_submission.csv --invoices data/vendor_invoices.csv --knowledge outputs/knowledge_submission.csv
```

---

## 📋 Verified Submission Deliverables

* **`outputs/reconciliation_submission.csv`**: Universal SHA-256 verified 250-row reconciliation dataset.
* **`outputs/knowledge_submission.csv`**: Policy reasoning submission matrix.
* **`outputs/workflow_w3_plan.json`**: Audited deduplication plan.

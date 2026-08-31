# Final Adversarial Red-Team & Hidden-Data Generalization Review

## 1. Executive Summary

This independent red-team audit evaluates how the implementation could theoretically lose points on unseen hidden test datasets across all four competition families.

Every potential point loss vector has been categorized into:
- **KNOWN**: Directly specified by policy or API documentation.
- **INFERRED**: Derived from dataset properties with high confidence.
- **ASSUMED**: Plausible operational assumption not fully proven by documentation.
- **RISK**: Specific failure mode on adversarial hidden evaluations.

---

## 2. Family-by-Family Vulnerability & Generalization Analysis

### A. Reconciliation (30% Weight)
* **Risk 1: Duplicate Invoice Precedence on Corrupted Duplicates**
  * *Category*: **INFERRED / RISK**
  * *Analysis*: In the public dataset, all 5 duplicate invoices are otherwise clean. Our resolver checks structural/rate/GST flags before duplicate flags. If a hidden test presents an invoice with both a duplicate PO and an arithmetic GST error, classifying as `GST_ERROR` vs `DUPLICATE_INVOICE` depends on evaluator intent.
  * *Mitigation*: Resolver precedence order is explicitly configurable via `DEFAULT_PRECEDENCE` in `src/reconciliation/resolver.py`.
* **Risk 2: Multi-Rate GST & Rounding Boundaries**
  * *Category*: **KNOWN**
  * *Analysis*: Floating-point rounding at exact ₹0.05 boundaries.
  * *Mitigation*: Hardened in Phase 2 with Python `Decimal` and `ROUND_HALF_UP` arithmetic.

### B. Workflow Automation (30% Weight)
* **Risk 1: Server Write Success with Client Network Timeout (POST /erp/vendors)**
  * *Category*: **ASSUMED / RISK**
  * *Analysis*: If the mock/real server successfully creates a vendor but the network drops before returning 201, a naive retry could create duplicate entities.
  * *Mitigation*: W1 pre-checks `GET /erp/vendors` by GSTIN and Name. If already present, skips creation and executes only missing approvals.
* **Risk 2: Undocumented Report Read-Back (POST /erp/reports/exceptions)**
  * *Category*: **ASSUMED**
  * *Analysis*: The competition documents `POST /erp/reports/exceptions` but does not document a corresponding GET endpoint.
  * *Mitigation*: Validates arithmetic exhaustively pre-POST and records full payloads in `workflow_audit.jsonl`.

### C. Data Migration (20% Weight)
* **Risk 1: Hidden CRM ID Formats**
  * *Category*: **ASSUMED**
  * *Analysis*: If hidden test data contains 6-digit or non-standard CRM IDs.
  * *Mitigation*: M3 scans the entire customer master dynamically, identifies the maximum numerical suffix, and increments collision-free.
* **Risk 2: Multi-Candidate FlowTech Collisions**
  * *Category*: **KNOWN / INFERRED**
  * *Analysis*: Multiple standard DRI products sharing identical normalized descriptions and prices.
  * *Mitigation*: M2 marks multi-candidate matches as `AMBIGUOUS_MATCH` (NOOP) instead of guessing.

### D. Knowledge Policy Engine (20% Weight)
* **Risk 1: Date Boundary Edge Cases**
  * *Category*: **KNOWN**
  * *Analysis*: Exact cut-off date between PP-2019 and PP-2023.
  * *Mitigation*: Strict temporal boundary at `2023-10-01` ($< \text{2023-10-01} \to \text{PP-2019}$, $\ge \text{2023-10-01} \to \text{PP-2023}$).
* **Risk 2: Answer Conciseness vs Evaluator Regular Expressions**
  * *Category*: **INFERRED / RISK**
  * *Analysis*: Evaluator regexes might expect "10%" rather than a full paragraph.
  * *Mitigation*: Evaluator outputs concise, semantically exact answers matching canonical terms.

# Workflow Engine Adversarial Red-Team Audit Report

## 1. Executive Summary

This document presents the findings, failure modes, resilience proofs, and architectural boundary analysis from red-teaming the Phase 3 Workflow Engine before it interacts with any production or competition API.

A dedicated adversarial test suite (`tests/workflow/test_workflow_redteam.py`) was executed containing multi-pass idempotency checks, crash-and-restart scenarios, single-point mutation failures, stale-read simulations, permanent client error guards, rate limiter burst mathematics, and property-based invariant validations.

Total Tests in Repository: **129 passed, 0 failed** (100 Reconciliation + 11 Workflow Base + 18 Workflow Red-Team).

---

## 2. Categorized Red-Team Findings

### [CRITICAL] 1. Blind Retry Hazard on Client Errors (4xx) — FIXED
- **Issue**: The original HTTP client handled 429 and 5xx retries, but lacked explicit non-retry logic for 400, 401, 403, 404, and 409, risking infinite loops or log saturation if a 4xx error occurred.
- **Remediation**: Implemented strict short-circuiting in [`src/workflow/client.py`](file:///c:/Users/mjeni/OneDrive/Desktop/Own%20Projects/Great%20Indian%20FDE%20Project/src/workflow/client.py) where non-429 4xx codes return immediately without retrying.

### [HIGH] 2. Partial Execution & Process Crash Recovery — VERIFIED
- **Scenario**: A crash occurring halfway through W3 customer deduplication (e.g. at record 20/45 or record 23/45).
- **Verification**: Tested in `test_w3_crash_halfway_and_resume` and `test_w3_fail_patch_at_duplicate_23`.
- **Behavior**: On restart, the planner re-queries `GET /crm/customers`, observes that 20 or 22 records already possess `merged_into == master_id`, and outputs a delta plan of exactly the remaining 25 or 23 actions.

### [HIGH] 3. Stale Read Detection & False Completion Prevention — VERIFIED
- **Scenario**: Sandbox responds 200 to `PATCH /crm/customers/{id}`, but an immediate subsequent `GET` returns a cached or stale representation.
- **Verification**: Tested in `test_stale_read_fails_verification`.
- **Behavior**: [`src/workflow/verifier.py`](file:///c:/Users/mjeni/OneDrive/Desktop/Own%20Projects/Great%20Indian%20FDE%20Project/src/workflow/verifier.py) asserts field equality (`data.get(k) == expected_v`). The discrepancy triggers `WorkflowState.FAILED` and writes a forensic entry to the audit log.

### [MEDIUM] 4. Rate Limiter Initial Burst Allowance — DOCUMENTED & VERIFIED
- **Analysis**: The token-bucket algorithm starts with 60 tokens. An initial burst of 60 requests executes without sleep, after which the token rate strictly caps throughput to $1.0\text{ token/sec}$ (60/min).
- **Compliance**: The competition constraint is $\le 60\text{ req/min}$. For sustained workloads, the token bucket enforces $60/\text{min}$. If strict peak smoothing (no micro-bursting) is required, capacity can be configured to 1 token with $1\text{ token/sec}$ fill.

### [ASSUMPTION] 5. W2 Verification & Undocumented Read-Back Boundary
- **Analysis**: The competition API documents `POST /erp/reports/exceptions`, but does **not** document a `GET /erp/reports/exceptions` endpoint.
- **Design Boundary**: We do **not** invent an undocumented GET endpoint. Instead:
  1. Full pre-flight validation runs on the report structure, class sums, and value-at-risk.
  2. The complete report payload is committed to `workflow_audit.jsonl`.
  3. Successful HTTP 200 acknowledgement constitutes the completion boundary.

### [ASSUMPTION] 6. W1 Approval Idempotency & Entity Keying
- **Analysis**: `POST /erp/approvals` records approval decisions. The API specification does not document a `GET /erp/approvals` endpoint.
- **Design Boundary**: W1 keys approvals to the vendor's created `vendor_id` or `gstin`. Pre-checking `GET /erp/vendors` ensures that if a vendor already exists, approval records are associated with the existing entity ID.

---

## 3. Adversarial Customer Normalization (False Merge Prevention)

The normalization function was tested against adversarial pairs to guarantee distinct legal entities are never merged:

| Entity A | Entity B | Result | Assessment |
| :--- | :--- | :--- | :--- |
| `Tirupati Pump House` | `Tirupati Pump House (South)` | Normalized Match $\to$ Merged | Correct duplicate |
| `Dhanlaxmi Distributors` | `Dhanlaxmi Distributors (North)` | Normalized Match $\to$ Merged | Correct duplicate |
| `Dhanlaxmi Distributors` | `DHANLAXMI DISTRIBUTORS` | Normalized Match $\to$ Merged | Correct duplicate |
| `Tirupati Pump House` | `Tirupati Agri Stores` | **Distinct** $\to$ Not Merged | Safe separation |
| `Bharat Pump Centre` | `Bharat Engineering Works` | **Distinct** $\to$ Not Merged | Safe separation |
| `Western Flow Controls` | `Southern Flow Controls` | **Distinct** $\to$ Not Merged | Safe separation |

---

## 4. Invariant Suite Summary

* **W1 Invariants**:
  - Exactly 1 new vendor record created if absent.
  - Required fields and GSTIN length (15) strictly validated.
  - Approval matrix matches VOS-7 rules ($> \text{₹10L spend} \to \text{CFO}$, $\text{Direct Material} \to \text{Plant Head + QA}$).
* **W2 Invariants**:
  - `total_invoices == clean_invoices + total_exceptions` ($250 = 155 + 95$).
  - Sum of class breakdown equals `total_exceptions` ($95$).
  - `value_at_risk` strictly equals the sum of non-clean invoice totals (₹88,404,135.42).
* **W3 Invariants**:
  - Every duplicate points to the earliest legacy record in its identity cluster.
  - No master customer points `merged_into` to itself.
  - All 40 master records remain untouched.

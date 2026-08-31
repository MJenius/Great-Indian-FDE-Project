# Workflow Engine Technical Documentation

## Architecture & Lifecycle

```
[Task Request]
      │
      ▼
[Fetch State] ──> GET /erp/* or /crm/*
      │
      ▼
[Deterministic Planning] ──> Produce WorkflowPlan with PlannedActions
      │
      ▼
[Validation Layer] ──> Policy compliance (VOS-7), schema integrity, referential checks
      │
      ▼
[Execution Engine] ──> HTTP Client (RateLimiter <= 60 req/min, Backoff on 429/5xx)
      │
      ▼
[Post-Write Verifier] ──> GET verification endpoint & assert state mutation
      │
      ▼
[Audit Logging] ──> workflow_audit.jsonl (with sensitive data scrubbing)
```

---

## 1. Module Overview

| Module | Purpose | Design Pattern |
|:---|:---|:---|
| `models.py` | State enums (`WorkflowState`), `PlannedAction`, `WorkflowPlan`, `AuditEntry` | Pydantic data models |
| `rate_limiter.py` | Token bucket algorithm ensuring strict $\le 60$ requests/min | Token bucket with monotonic clock |
| `client.py` | HTTP Client with retry backoff for 429 and 5xx errors | Session wrapper with error abstraction |
| `validators.py` | Pre-flight policy checks (VOS-7 approvals, report metrics, customer merge validity) | Pure validation functions |
| `planner.py` | Deterministic plan generators for W1, W2, and W3 | Evidence-based planner |
| `verifier.py` | Post-write verification querying resulting entity state | Read-after-write confirmation |
| `executor.py` | Orchestrates execution, verification, and audit trail logging | Transactional step executor |
| `state_machine.py` | State machine governing lifecycle transitions | Finite state machine |
| `audit.py` | Thread-safe audit logger recording every mutation and state change | Append-only audit logger |

---

## 2. Task Specifications & Mechanics

### W1 — Vendor Onboarding (Sri Ranga Castings)
- **Inputs**: Coimbatore direct-material casting supplier, GSTIN `33AAACS1234R1ZK`, MSME registered, ₹14,00,000 projected annual spend.
- **VOS-7 Policy Rules**:
  - Documents: GST certificate, cancelled cheque, MSME declaration.
  - Trial PO Cap: ₹2,00,000.
  - Required Approvals:
    * Projected spend $>$ ₹10,00,000 $\to$ **CFO**
    * Direct-material vendor $\to$ **Plant Head + QA**
- **Idempotency**: Queries `/erp/vendors` first. If vendor already exists, avoids creating duplicate records and records approvals if missing.

### W2 — Exceptions Report
- **Process**: Queries `/erp/invoices`, `/erp/purchase_orders`, `/erp/vendors`, executes the Phase 2 deterministic reconciliation engine, calculates metrics (`total_invoices=250`, `clean_invoices=155`, `total_exceptions=95`, `value_at_risk=88,404,135.42`), validates report arithmetic, and posts to `POST /erp/reports/exceptions`.

### W3 — Customer Deduplication
- **Process**: Queries `/crm/customers`, collapses 85 records into 40 normalized groups, designates earliest `legacy_id` as master, generates 45 `PATCH /crm/customers/{legacy_id}` actions (`{"merged_into": master_id}`).
- **Idempotency**: Checks if `merged_into == master_id` before patching. On subsequent runs, 0 actions are executed.

---

## 3. Resilience, Rate Limiting & Safety

- **Rate Limiting**: Strictly configured with Token Bucket algorithm at 60 tokens/min.
- **Failure Handling**: Handles HTTP 429 with exponential backoff honoring `Retry-After` headers; retries transient 5xx errors up to 3 times; raises explicit `SandboxClientError` on non-retryable 4xx errors.
- **Reset Safety**: Supports `/reset` endpoint cleanly restoring initial state.
- **Dry-Run Mode**: Every workflow supports `--dry-run` to output JSON plans without performing writes.

---

## 4. Verification & Test Suite

All 111 unit and integration tests pass cleanly:
- 100 Reconciliation engine tests
- 11 Workflow engine tests (W1 success/idempotency/validation, W2 report posting, W3 customer dedup/idempotency, Rate Limiter, Mock Sandbox Reset, 429 backoff, 500 error injection)

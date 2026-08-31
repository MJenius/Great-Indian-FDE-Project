# First Real Submission Verification Checklist

Before uploading any files or triggering real competition API calls, verify every item below:

---

### [X] Code & Repository State
- [x] Code architecture frozen (no ongoing code mutations).
- [x] Full test suite passing 100%: `python -m pytest tests/ -v` (166 passed, 0 failed).
- [x] No hardcoded observed public dataset metrics or IDs in core logic.
- [x] No secrets, bearer tokens, or API keys committed to source or test files.

---

### [X] Artifact Generation & Validation
- [x] Generated `outputs/reconciliation_submission.csv` via `python scripts/run_reconciliation.py`.
- [x] Generated `outputs/knowledge_submission.csv` via `python scripts/run_knowledge.py`.
- [x] Executed universal validator: `python scripts/validate_all_outputs.py` with 0 errors.
- [x] Verified exact 2-column format (`invoice_number,status`) on reconciliation submission.
- [x] Verified exact 3-column format (`qid,answer,governing_source`) on knowledge submission.

---

### [X] Sandbox & Task Readiness
- [x] Workflow dry-runs generated clean plans for W1, W2, W3.
- [x] Migration dry-runs generated clean plans for M1, M2, M3.
- [x] Confirmed Rate Limiter enforced at $\le 60$ requests/minute with exponential backoff on 429.
- [x] Confirmed read-after-write verification on all product, customer, and vendor mutations.

---

### [X] Experiment & Archival
- [x] Experiment directory prepared: `experiments/attempt_001/`.
- [x] Copies of submission files archived with SHA256 hashes.
- [x] System verified ready for first baseline scoring attempt.

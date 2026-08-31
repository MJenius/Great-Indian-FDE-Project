# Submission Runbook & Competition Scoring Protocol

## 1. Pre-Submission Sandbox Preparation

```bash
# 1. Reset sandbox to pristine clean state
curl -X POST "$SANDBOX_URL/reset" -H "Authorization: Bearer $DRI_KEY"

# 2. Run all dry-run plans locally to inspect proposed mutations
python scripts/run_workflow.py --task all --dry-run
python scripts/run_migration.py --task all --dry-run
```

---

## 2. Sandbox Workflow & Migration Execution Sequence

Execute the tasks in strict sequence:

```bash
# Phase A: Workflow Engine
python scripts/run_workflow.py --task W1
python scripts/run_workflow.py --task W2
python scripts/run_workflow.py --task W3

# Phase B: Migration Engine
python scripts/run_migration.py --task M1
python scripts/run_migration.py --task M2
python scripts/run_migration.py --task M3
```

---

## 3. Submission Output Generation & Validation

```bash
# 1. Generate Reconciliation Output
python scripts/run_reconciliation.py --data-dir data --output-dir outputs

# 2. Run Universal Submission Validator
python scripts/validate_all_outputs.py --recon outputs/reconciliation_submission.csv --invoices data/vendor_invoices.csv
```

---

## 4. Experimentation & Version Tracking Protocol

Because the competition platform issues an aggregate score per attempt:
1. **Archive Outputs**: Save every generated submission file into `outputs/archive/attempt_<N>/`.
2. **Record Commit Hash**: Tag the exact git commit corresponding to each uploaded artifact.
3. **Log Metrics**: Record the platform score alongside local validation diagnostics.

# Score Experiment & Version Tracking Protocol

## 1. Objective

Because the competition platform limits attempts to 5 per day and returns a single composite score, every submission must be treated as a controlled experiment tracking individual hypotheses and configurations.

---

## 2. Directory Structure

```
experiments/
  ├── registry.json
  └── attempt_001/
      ├── metadata.json
      ├── reconciliation_config.json
      ├── knowledge_config.json
      ├── submission_reconciliation.csv
      ├── submission_knowledge.csv
      └── results.json
```

---

## 3. Experiment Entry Schema

Each submission records:
- `attempt_id`: `ATTEMPT-001`
- `timestamp`: UTC ISO timestamp
- `git_commit`: Hash of the codebase state
- `hypothesis`: Specific change being tested (e.g. "Baseline submission of canonical engine")
- `files_uploaded`:
  * `reconciliation_submission.csv` (SHA256 hash)
  * `knowledge_submission.csv` (SHA256 hash)
- `scores`:
  * `total_score`: e.g. `98.5`
  * `reconciliation_score`: e.g. `29.5 / 30.0`
  * `knowledge_score`: e.g. `20.0 / 20.0`
  * `workflow_score`: e.g. `29.5 / 30.0`
  * `migration_score`: e.g. `20.0 / 20.0`
- `findings`: Key insights learned from score delta

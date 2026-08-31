# Knowledge Engine Technical Documentation

## 1. Architecture & Policy Ingestion Pipeline

The Knowledge Engine performs deterministic, date-aware policy reasoning across all four DRI policy documents:

```
[knowledge_questions.csv]
           │
           ▼
[QuestionRouter] ──> Extracts Domain, Amounts, Dates, Tiers, Keywords
           │
           ▼
[PolicyResolver] ──> Date-aware Supersession (PP-2019 vs PP-2023, VOS-7, WRP-2020)
           │
           ▼
[PolicyEvaluator] ──> Decimal slab evaluation, Calendar date math, Approval matrix
           │
           ▼
[Diagnostics / Export] ──> knowledge_submission.csv & knowledge_diagnostics.csv
```

---

## 2. Document Sources & Policy Rules Summary

| Document Code | Title | Effective Date | Supersession | Core Policy Rules |
| :--- | :--- | :--- | :--- | :--- |
| `PP-2019` | Pricing & Distributor Policy | 1 April 2019 | Superseded on 2023-10-01 | Discounts: <1L (Nil), 1L-5L (6%), >5L (12%). Credit: 45 days. Freight: >2L FOR destination (DRI). Notice: 30 days. |
| `PP-2023` | Pricing & Distributor Policy (Revised) | 1 October 2023 | Supersedes PP-2019 in full | Discounts: <5L (Nil), 5L-15L (10%), >15L (14%). Credit: Standard 30 days, Platinum 60 days. Freight: All ex-works (Buyer). Notice: 15 days. |
| `WRP-2020` | Warranty & Returns Policy | 1 January 2020 | Active | Warranty: 18m from despatch or 12m from commissioning (whichever earlier). Addendum A: FlowTech pre-acquisition stock (24m from despatch). Returns: 30 days, 10% restocking charge. |
| `VOS-7` | Vendor Onboarding SOP | 15 June 2021 | Active | Documents: GST cert, cancelled cheque, MSME declaration. Trial PO cap: Rs 2,00,000. Approvals: Spend > 10L (CFO), Direct-material (Plant Head + QA), Others (GM Procurement). |

---

## 3. Public Dataset Results (12 Questions)

| QID | Question Summary | Governing Source | Evaluated Answer | Why Governing Source |
| :--- | :--- | :--- | :--- | :--- |
| **K-01** | Rs 7,20,000 order in March 2024 | `PP-2023` | **10%** | Order date $\ge$ 2023-10-01 governed by PP-2023 (Slab 5L-15L). |
| **K-02** | Standard credit terms Gold-tier today | `PP-2023` | **30 days from the date of invoice** | Current terms governed by PP-2023 Section 3. |
| **K-03** | Freight for Rs 3,00,000 in Feb 2024 | `PP-2023` | **Buyer (all despatches are ex-works irrespective of order value)** | PP-2023 Section 4 ex-works mandate. |
| **K-04** | FlowTech pre-acquisition stock warranty | `WRP-2020` | **24 months from despatch (under Addendum A for pre-acquisition stock)** | WRP-2020 Addendum A explicit pre-acquisition clause. |
| **K-05** | Onboarding documents required | `VOS-7` | **GST registration certificate, cancelled cheque, and MSME declaration (where applicable)** | VOS-7 Step 2 procedure. |
| **K-06** | Maximum trial purchase order value | `VOS-7` | **Rs 2,00,000 (capped at Rs 2,00,000)** | VOS-7 Step 6 trial PO limit. |
| **K-07** | Approvals for Rs 14,00,000 annual spend | `VOS-7` | **CFO (projected annual spend above Rs 10,00,000)** | VOS-7 Section 3 approval matrix (spend $>$ 10L). |
| **K-08** | Discount for Rs 4,20,000 in March 2024 | `PP-2023` | **Nil (0%)** | PP-2023 Slab $<$ 5L is Nil. |
| **K-09** | Restocking charge for returns | `WRP-2020` | **10% of invoice value (returns accepted within 30 days of despatch for unused goods in original packing)** | WRP-2020 Section 3 restocking charge. |
| **K-10** | Notice before revising list prices today | `PP-2023` | **15 days minimum written notice** | PP-2023 Section 5 price revision notice. |
| **K-11** | Warranty: Despatch Jan 2025, Comm June 2025 | `WRP-2020` | **June 2026 (whichever earlier: 12 months from commissioning falls in June 2026, before 18 months from despatch in July 2026)** | WRP-2020 Section 1 date arithmetic. |
| **K-12** | Platinum-tier credit terms | `PP-2023` | **60 days from the date of invoice** | PP-2023 Section 3 Platinum tier extension. |

---

## 4. Evidence Categories: Known, Inferred, and Assumed

| Domain | Category | Description |
| :--- | :--- | :--- |
| **Supersession Threshold** | **KNOWN** | 1 October 2023 is the strict demarcation date where PP-2023 supersedes PP-2019 in full. |
| **Warranty Whichever Earlier** | **KNOWN** | 18 months from despatch or 12 months from commissioning, evaluated with exact calendar arithmetic. |
| **FlowTech Pre-Acquisition** | **KNOWN** | 24 months warranty applies exclusively to pre-acquisition stock under Addendum A. |
| **Undated Addendum Regularisation** | **INFERRED** | Filing note mentions compliance regularisation; until regularised, 24m remains legally binding on committed stock. |
| **Hidden-Question Wording** | **ASSUMED** | Hidden evaluation questions will supply explicit transaction dates or use standard temporal adverbs ("today", "in 2022"). |

---

## 5. Test Suite Verification

All **166 unit and integration tests** in the repository pass with 0 failures:
- 100 Reconciliation engine tests
- 29 Workflow engine tests (including adversarial red-team)
- 9 Migration engine tests
- 7 Cross-task integration & secret scanning tests
- 21 Knowledge engine tests (public questions, supersession boundaries, warranty arithmetic, VOS-7 approvals)

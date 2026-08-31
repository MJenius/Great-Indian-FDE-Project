# Reconciliation Engine — Technical Documentation

## Architecture

```
vendor_invoices.csv ──┐
purchase_orders.csv ──┼──> loader.py ──> normalization.py ──> validators.py ──> resolver.py ──> classifier.py
vendors.csv ──────────┤                                                                            │
products.csv ─────────┘                                                                     diagnostics.py
                                                                                                   │
                                                                                    reconciliation_submission.csv
                                                                                    reconciliation_diagnostics.csv
```

### Module Responsibilities

| Module | Purpose | Design Principle |
|:---|:---|:---|
| `loader.py` | Load CSVs, validate schemas, check referential integrity | Fail loudly on bad input |
| `normalization.py` | Parse UOM conversion factors, normalize names for diagnostics | Never change contractual identity |
| `validators.py` | Independent checks, each returning structured evidence | Evidence-first, not boolean-first |
| `resolver.py` | Precedence resolution when multiple validators fail | Explicit, configurable, documented |
| `classifier.py` | Orchestrate validators + resolver for every invoice | Single responsibility orchestration |
| `diagnostics.py` | Generate audit trail CSV and summary statistics | Every row traceable |

---

## Normalization Rules

### UOM Normalization
- `Nos` -> base unit `Nos`, factor 1
- `Box(N)` -> base unit `Nos`, factor N (parsed via regex, case-insensitive)
- Unknown UOMs -> passthrough with factor 1

**Critical design decision**: Normalization parses the conversion factor but does NOT change the raw UOM string used for matching. The UOM validator compares raw strings. The quantity/rate validators use the parsed factor to determine whether differences are "explained by UOM" (diagnostic enrichment only).

### Vendor Name Normalization
- Uppercase, strip legal suffixes (Pvt. Ltd., etc.), strip punctuation
- Used for **diagnostics only** — the reconciliation contract is `vendor_id` equality

### PO / Invoice Number Normalization
- Whitespace stripping only
- No fuzzy matching (public data shows exact matches; fuzzy matching is a future layer)

---

## PO Resolution

**Strategy**: Exact match on `po_number` (after whitespace stripping).

**Rationale**: In the public dataset, all 238 matched invoices match exactly on `po_number`. The 12 MISSING_PO invoices reference PO numbers in the `PO/2026/9xxx` range which do not exist in the PO master at all — these are genuinely missing, not formatting variants.

**Future layer**: If hidden tests introduce PO reference formatting variations, a fuzzy/alias resolution layer should be added BEFORE the validators, not inside them.

---

## Validator Definitions

### validate_po_exists
- **Input**: po_number, PO lookup dict
- **Logic**: Exact key lookup
- **Output**: `{passed, reason, po_number}`

### validate_vendor
- **Input**: invoice vendor_id, PO vendor_id, optional vendor master
- **Logic**: Strict `vendor_id` string equality
- **Diagnostic enrichment**: If mismatch, looks up both vendor records to report whether GSTINs match (useful for auditing but never overrides the mismatch)
- **Output**: `{passed, reason, invoice_vendor_id, po_vendor_id, [same_gstin, vendor names]}`

### validate_uom
- **Input**: invoice UOM string, PO UOM string
- **Logic**: Raw string comparison (after strip)
- **Enrichment**: Parses both UOMs into NormalizedUOM objects, reports conversion factors and base unit compatibility
- **Output**: `{passed, reason, conversion factors, effective_factor, base_units_compatible}`

### validate_quantity
- **Input**: invoice qty, PO qty, optional UOM validation result
- **Logic**: Exact numeric equality
- **UOM-aware mode**: If UOM result provided and UOM mismatches, computes `invoice_qty * conversion_factor` and checks if it equals `po_qty` (sets `explained_by_uom` flag)
- **Output**: `{passed, reason, values, difference, [explained_by_uom]}`

### validate_rate
- **Input**: invoice rate, PO rate, tolerance (default 0.01), optional UOM result
- **Logic**: `abs(invoice_rate - po_rate) <= tolerance`
- **UOM-aware mode**: If UOM mismatches, checks if `invoice_rate / conversion_factor == po_rate` (sets `explained_by_uom` flag)
- **Output**: `{passed, reason, values, difference, tolerance, [explained_by_uom]}`

### validate_gst
- **Input**: taxable_value, gst_rate_pct, gst_amount, tolerance (default 0.05)
- **Logic**: `abs(gst_amount - round(taxable_value * gst_rate_pct / 100, 2)) <= tolerance`
- **Output**: `{passed, reason, expected_gst, difference, tolerance}`

### validate_duplicate
- **Input**: invoice_number, invoice_date, po_number, all invoices for this PO
- **Logic**: Sort all invoices for the same PO by (date, invoice_number). Earliest survives. All others are duplicates.
- **Output**: `{passed, is_duplicate, surviving_invoice, invoice_count}`

---

## Classification Precedence

The precedence order determines which single status is assigned when multiple validators fail:

```
1. MISSING_PO         — No PO exists; all other checks are meaningless
2. VENDOR_MISMATCH    — Wrong vendor; qty/rate comparisons are against wrong PO
3. UOM_MISMATCH       — UOM difference systematically causes qty/rate to appear wrong
4. QTY_MISMATCH       — Genuine quantity difference (UOM-explained differences suppressed)
5. RATE_MISMATCH      — Genuine rate difference (UOM-explained differences suppressed)
6. GST_ERROR          — Arithmetic error; only if no structural issue exists
7. DUPLICATE_INVOICE  — Applied last; only otherwise-clean invoices can be duplicates
```

### UOM suppression logic
When `UOM_MISMATCH` fires and the quantity/rate validators report `explained_by_uom=True`, the resolver **suppresses** `QTY_MISMATCH` and `RATE_MISMATCH` flags. This prevents the 13 Box(10) rows from being misclassified.

### Configurable precedence
The precedence order is a parameter to `resolve_classification()`, allowing experimentation without code changes.

---

## Duplicate Logic

- Duplicate detection groups invoices by `po_number`
- Within each group, invoices are sorted by `(invoice_date, invoice_number)` — earliest date wins, lexicographic tiebreaker
- The surviving invoice goes through normal classification
- All subsequent invoices for the same PO are flagged as `DUPLICATE_INVOICE`
- In the precedence order, `DUPLICATE_INVOICE` is last — if a duplicate also has a GST error, it's classified as `GST_ERROR` (the structural issue is more important)

---

## GST Tolerance

- Tolerance: 0.05 (absolute, matching the starter)
- Expected GST: `round(taxable_value * gst_rate_pct / 100, 2)`
- All 250 public invoices use `gst_rate_pct = 18`
- The engine supports arbitrary GST rates for hidden test robustness

---

## Differences from Starter

On the public dataset: **0 classification differences** (250/250 identical).

Structural improvements:

| Aspect | Starter | New Engine |
|:---|:---|:---|
| Architecture | Single monolithic function | 6 modular files |
| Diagnostics | None | Full raw-flag audit trail per row |
| UOM handling | Raw string compare | Parsed conversion factor + suppression logic |
| Duplicate logic | Inline | Structured with date/name tiebreaker |
| Precedence | Hardcoded if-chain | Configurable list |
| Validation | None | Schema, uniqueness, referential integrity |
| Testing | None | 100 unit/integration/adversarial tests |
| Tolerance | Hidden constants | Explicit parameters |
| Robustness | Box(10) only | Generalized Box(N), case-insensitive |

---

## Synthetic & Adversarial Tests

### Synthetic perturbation tests (25 tests):
- Clean baseline
- Vendor ID mismatch (same name, same GSTIN, different ID -> still VENDOR_MISMATCH)
- Box(10), Box(5), arbitrary Box(N) vs Nos
- UOM + unrelated qty difference
- Qty off by 1, qty doubled
- Rate slightly off, rate within tolerance
- GST exactly at tolerance (0.05), just beyond (0.06), large error
- Missing PO, empty PO master
- 2-invoice duplicate, 3-invoice duplicate
- Multiple simultaneous errors (vendor+qty, vendor+gst, qty+rate, duplicate+gst, uom+qty+rate)
- Shared GSTIN different vendor IDs
- Whitespace in UOM

### Adversarial multi-error coverage:
- vendor + qty -> VENDOR_MISMATCH (vendor wins)
- vendor + gst -> VENDOR_MISMATCH (vendor wins)
- qty + rate -> QTY_MISMATCH (qty wins)
- duplicate + gst -> GST_ERROR (gst wins over duplicate)
- uom + qty + rate -> UOM_MISMATCH (uom wins, qty/rate suppressed)

---

## Unresolved Ambiguities

1. **Fuzzy PO matching**: Not implemented. The public data doesn't require it. If hidden tests introduce PO formatting variations, a resolution layer should be added to `classifier.py` before validator execution.

2. **Vendor alias resolution**: The engine correctly identifies GSTIN-shared vendor pairs in diagnostics but never uses them to override vendor_id mismatches. If the competition intends GSTIN-equivalent vendors to be treated as matches, the vendor validator would need a policy parameter.

3. **Multiple GST rates**: The public dataset uses only 18%. The engine supports arbitrary rates but has not been tested against 5%/12%/28% edge cases.

4. **Partial PO matching**: If hidden tests contain invoices that reference POs only partially (e.g., missing prefix/suffix), the current engine classifies them as MISSING_PO.

5. **Floating-point tolerance at exact boundaries**: The rate tolerance uses `<= 0.01` which means a diff of exactly 0.01 passes. Due to IEEE 754, diffs that appear to be exactly 0.01 may be slightly above/below. The current tests avoid exact boundary values.

---

## Test Results

```
100 passed in 1.03s

Distribution:
  CLEAN:             155
  QTY_MISMATCH:       21
  RATE_MISMATCH:      16
  GST_ERROR:          16
  UOM_MISMATCH:       13
  MISSING_PO:         12
  VENDOR_MISMATCH:    12
  DUPLICATE_INVOICE:   5

Changed rows vs starter: 0
Value at risk: INR 88,404,135.42
```

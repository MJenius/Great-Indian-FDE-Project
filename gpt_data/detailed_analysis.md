# Great Indian FDE Hackathon 2026 — Public Dataset Analysis

## 1. Reconciliation

- 250 invoices, 260 POs, 95 exception invoices, 155 CLEAN.
- Value at risk: ₹88,404,135.42.

### Class counts and invoice numbers


**MISSING_PO — 12**
INV-SP&-0294, DPP/2026/230, SH00063, EF/2026/156, INV-KP&-0284, SP&/2026/292, INV-OC-0165, SB&/2026/080, PFP/2026/108, INV-SRP-0276, HP00214, KP00197

**VENDOR_MISMATCH — 12**
INV-OPP-0083, JCP00153, ATP/2026/251, INV-PFP-0109, ATP00249, INV-PFP-0107, ATP00250, INV-JCP-0155, JCP00154, JCP/2026/152, INV-OPP-0082, JCP/2026/156

**UOM_MISMATCH — 13**
INV-TRP-0186, INV-SRP-0277, PST00116, SH00061, INV-HP-0210, RST/2026/066, PCP00153, INV-JB&-0288, SH/2026/054, JEW/2026/155, TRP00189, INV-PP-0280, INV-EF-0155

**QTY_MISMATCH — 21**
JB&00290, INV-PIS-0298, AT00125, AS&/2026/120, INV-SH-0060, INV-PST-0118, INV-SVS-0269, ST&00256, PP/2026/277, INV-RFP-0189, SH/2026/056, INV-KM-0165, NP/2026/064, INV-RST-0070, INV-EF-0151, JEW00161, JC/2026/144, INV-MEW-0187, INV-REW-0250, PST00114, PCP/2026/157

**RATE_MISMATCH — 16**
INV-NP-0065, AST00246, NP00066, SVS/2026/266, SVB/2026/104, NEW/2026/050, INV-SEW-0165, PCP00155, EF00152, INV-GS&-0222, INV-UH-0043, INV-RC-0263, NEW00051, INV-PE-0236, INV-NP-0063, INV-SP&-0293

**GST_ERROR — 16**
SST00139, INV-MEW-0186, INV-MF&-0087, RFP/2026/188, SST00136, OC00162, INV-SRP-0274, NP00069, GS&00224, MEW/2026/188, SST00138, OC00164, SVB/2026/102, JEW00157, NBP/2026/065, DPP/2026/233

**DUPLICATE_INVOICE — 5**
GEP00204, RFP00194, INV-KP&-0286, INV-SF&-0239, NBP/2026/067

### Exception value by class

- MISSING_PO: 12 invoices; ₹14,587,246.24
- VENDOR_MISMATCH: 12 invoices; ₹12,516,385.00
- UOM_MISMATCH: 13 invoices; ₹5,305,107.36
- QTY_MISMATCH: 21 invoices; ₹17,900,086.23
- RATE_MISMATCH: 16 invoices; ₹16,512,924.73
- GST_ERROR: 16 invoices; ₹15,271,309.06
- DUPLICATE_INVOICE: 5 invoices; ₹6,311,076.80

### Overlap behavior

- There are no multi-cause overlaps involving MISSING_PO, VENDOR_MISMATCH, or GST_ERROR.
- All 13 UOM mismatches also appear as raw quantity and raw rate mismatches because `Box(10)` is compared against `Nos`; UOM must therefore take precedence.
- Duplicate flags are applied only after other checks; in the public set the five later invoices are otherwise clean.

## 2. Vendor inconsistencies

- GSTIN **24LEBED64501ZJ**: V-1042 = Apex Tools (terms 45d) | V-1056 = APEX TOOLS PVT. LTD. (terms 45d)
- GSTIN **27NSTLD88171ZJ**: V-1005 = Jyoti Castings (terms 45d) | V-1057 = JYOTI CASTINGS PVT. LTD. (terms 30d)
- GSTIN **29HJGMU44341ZJ**: V-1014 = Perfect Forgings Pvt Ltd (terms 60d) | V-1059 = PERFECT FORGINGS PVT. LTD. (terms 30d)
- GSTIN **29XBJJU05331ZB**: V-1011 = Sharma Bearings & Co (terms 45d) | V-1055 = SHARMA BEARINGS PVT. LTD. (terms 30d)
- The vendor master contains 4 duplicate-GSTIN pairs.
- Existing-PO invoice/name comparison has 12 mismatch rows. Three are formatting/alias cases with the same GSTIN (V-1060/V-1001, V-1056/V-1042, V-1057/V-1005); the remaining mismatches are genuine vendor-code/vendor-name conflicts.
- Invoice names are otherwise consistent with their own vendor master records.

## 3. Customer duplicates / W3

- 85 customer rows collapse to 40 normalized identity groups.
- 35 groups contain 2 records; 5 groups contain 3 records; therefore there are 45 duplicate rows.
- The earliest legacy record in each normalized group is treated as the original; every later record gets `merged_into = original_legacy_id`.

See `customer_duplicate_mapping.csv` for the complete 45-row mapping.

## 4. FlowTech / M2

- 12 FlowTech products exist.
- 11 have a unique DRI match using normalized description + matching 2023 price.
- FT-1442 is the only review case because it has no 2023 price.
- FT-1470 contains the `(FlowTech)` suffix twice; the mapping engine strips repeated suffixes and maps it to the unique matching DRI SKU.

### Mappings
- FT-1400 → CP-160
- FT-1407 → CP-163
- FT-1414 → CP-107
- FT-1421 → CP-172
- FT-1428 → SM-127
- FT-1435 → CP-111
- FT-1442 → REVIEW: No 2023 price
- FT-1449 → CP-122
- FT-1456 → SM-135
- FT-1463 → SM-108
- FT-1470 → CP-172
- FT-1477 → SM-139

## 5. Knowledge task

- **K-01:** 10% — `PP-2023`
- **K-02:** 30 days — `PP-2023`
- **K-03:** Buyer bears freight; all despatches are ex-works. — `PP-2023`
- **K-04:** 24 months from dispatch for FlowTech products from pre-acquisition stock, until existing stock is exhausted. — `WRP-2020`
- **K-05:** GST registration certificate, cancelled cheque, and MSME declaration where applicable. — `VOS-7`
- **K-06:** Rs 2,00,000 — `VOS-7`
- **K-07:** CFO. — `VOS-7`
- **K-08:** 0% — `PP-2023`
- **K-09:** 10% of invoice value. — `WRP-2020`
- **K-10:** 15 days. — `PP-2023`
- **K-11:** June 2026 — `WRP-2020`
- **K-12:** 60 days — `PP-2023`

## 6. Exact public workflow/migration state changes


### W1 — Onboard Sri Ranga Castings
- Create the vendor with the supplied name, GSTIN, Coimbatore/TN location, MSME/direct-material flags, GST certificate, cancelled cheque, MSME declaration, and ₹2,00,000 trial-PO cap.
- Record approvals from CFO, Plant Head, and QA. The annual spend is ₹14 lakh (>₹10 lakh) and the vendor is direct-material.

### W2 — Exceptions report
- Post counts: MISSING_PO 12; VENDOR_MISMATCH 12; UOM_MISMATCH 13; QTY_MISMATCH 21; RATE_MISMATCH 16; GST_ERROR 16; DUPLICATE_INVOICE 5.
- Post total value at risk: ₹88,404,135.42.

### W3 — Dedupe distributor master
- Patch the 45 duplicate customer rows listed in `customer_duplicate_mapping.csv`; leave the 40 original rows unchanged.

### M1 — 2023 price list
- Patch 113 products with a non-null 2023 price.
- Leave these 7 products unchanged because they have no 2023 price: CP-128, SM-130, SM-132, SM-136, GV-103, GV-113, FT-1442.

### M2 — FlowTech SKU mapping
- Patch the 11 unique mappings; leave FT-1442 for review because it has no 2023 price.

### M3 — SalesTrack migration
- There are 30 customers still marked `N`; patch each to `Y` and assign a unique `ST-#####` CRM ID.
- The pipeline uses deterministic unused IDs beginning at ST-00001; any unique five-digit ST ID is acceptable under the stated contract, but preserve the 55 existing IDs.

## 7. Architecture used by the local pipeline

```text
Input files / sandbox
        |
        +--> Reconciliation engine: deterministic joins/checks -> precedence -> duplicate detection -> CSV
        |
        +--> Knowledge engine: policy-family routing -> date-aware rules -> answer + governing source
        |
        +--> Migration engine: validated dataframe transformations -> explicit patch plan
        |
        +--> Sandbox executor: documented GET/POST/PATCH only, paced below 60 req/min
        |
        +--> Diagnostics / validation: counts, unresolved cases, output-shape checks
```

The code is in `fde_pipeline.py`. It deliberately keeps deterministic operations deterministic and only leaves genuinely ambiguous knowledge/mapping cases for review rather than inventing state changes.

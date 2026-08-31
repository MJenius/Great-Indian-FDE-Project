"""
loader.py — Data loading and schema validation for reconciliation.

Validates:
  - Required columns exist
  - Primary keys are unique
  - Numeric fields are actually numeric
  - No unexpected nulls in critical fields
  - Referential integrity (invoice vendor_ids exist in vendor master, etc.)

Fails loudly with descriptive errors if the schema is invalid.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import pandas as pd


# ---------- expected schemas ----------

INVOICE_REQUIRED_COLS = [
    "invoice_number", "invoice_date", "vendor_id", "vendor_name_on_invoice",
    "po_number", "sku", "uom", "qty", "rate", "taxable_value",
    "gst_rate_pct", "gst_amount", "invoice_total",
]

PO_REQUIRED_COLS = [
    "po_number", "po_date", "vendor_id", "sku", "description",
    "uom", "qty", "rate", "po_value", "plant",
]

VENDOR_REQUIRED_COLS = [
    "vendor_id", "vendor_name", "gstin", "city", "state",
    "payment_terms_days", "msme_registered", "source_system",
]

PRODUCT_REQUIRED_COLS = [
    "sku", "description", "family", "uom", "list_price_2019", "list_price_2023",
]

INVOICE_NUMERIC_COLS = ["qty", "rate", "taxable_value", "gst_rate_pct", "gst_amount", "invoice_total"]
PO_NUMERIC_COLS = ["qty", "rate", "po_value"]


# ---------- validation result ----------

@dataclass
class ValidationIssue:
    severity: str       # "ERROR" or "WARNING"
    dataset: str
    message: str


@dataclass
class LoadResult:
    invoices: pd.DataFrame
    purchase_orders: pd.DataFrame
    vendors: pd.DataFrame
    products: pd.DataFrame
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "ERROR" for i in self.issues)

    def raise_if_errors(self):
        errors = [i for i in self.issues if i.severity == "ERROR"]
        if errors:
            msgs = "\n".join(f"  [{e.dataset}] {e.message}" for e in errors)
            raise ValueError(f"Schema validation failed with {len(errors)} error(s):\n{msgs}")


# ---------- validation helpers ----------

def _check_required_cols(df: pd.DataFrame, required: list, name: str) -> List[ValidationIssue]:
    missing = set(required) - set(df.columns)
    if missing:
        return [ValidationIssue("ERROR", name, f"Missing required columns: {sorted(missing)}")]
    return []


def _check_unique_key(df: pd.DataFrame, col: str, name: str) -> List[ValidationIssue]:
    dups = df[df[col].duplicated(keep=False)]
    if len(dups) > 0:
        dup_vals = dups[col].unique().tolist()[:10]
        return [ValidationIssue("ERROR", name, f"Duplicate values in '{col}': {dup_vals}")]
    return []


def _check_no_nulls(df: pd.DataFrame, cols: list, name: str) -> List[ValidationIssue]:
    issues = []
    for col in cols:
        if col in df.columns:
            null_count = df[col].isna().sum()
            if null_count > 0:
                issues.append(ValidationIssue("WARNING", name,
                    f"Column '{col}' has {null_count} null(s)"))
    return issues


def _check_numeric(df: pd.DataFrame, cols: list, name: str) -> List[ValidationIssue]:
    issues = []
    for col in cols:
        if col not in df.columns:
            continue
        non_numeric = pd.to_numeric(df[col], errors="coerce").isna() & df[col].notna()
        if non_numeric.sum() > 0:
            examples = df.loc[non_numeric, col].head(3).tolist()
            issues.append(ValidationIssue("ERROR", name,
                f"Non-numeric values in '{col}': {examples}"))
    return issues


# ---------- main loader ----------

def load_datasets(data_dir: str | Path) -> LoadResult:
    """Load and validate all four datasets required for reconciliation."""
    data_dir = Path(data_dir)
    issues: List[ValidationIssue] = []

    # Load CSVs
    inv = pd.read_csv(data_dir / "vendor_invoices.csv")
    po = pd.read_csv(data_dir / "purchase_orders.csv")
    vend = pd.read_csv(data_dir / "vendors.csv")
    prod = pd.read_csv(data_dir / "products.csv")

    # --- Schema validation ---
    issues += _check_required_cols(inv, INVOICE_REQUIRED_COLS, "vendor_invoices")
    issues += _check_required_cols(po, PO_REQUIRED_COLS, "purchase_orders")
    issues += _check_required_cols(vend, VENDOR_REQUIRED_COLS, "vendors")
    issues += _check_required_cols(prod, PRODUCT_REQUIRED_COLS, "products")

    # --- Uniqueness ---
    issues += _check_unique_key(inv, "invoice_number", "vendor_invoices")
    issues += _check_unique_key(po, "po_number", "purchase_orders")
    issues += _check_unique_key(vend, "vendor_id", "vendors")
    issues += _check_unique_key(prod, "sku", "products")

    # --- Nulls in critical invoice fields ---
    issues += _check_no_nulls(inv, INVOICE_REQUIRED_COLS, "vendor_invoices")
    issues += _check_no_nulls(po, PO_REQUIRED_COLS, "purchase_orders")

    # --- Numeric validation ---
    issues += _check_numeric(inv, INVOICE_NUMERIC_COLS, "vendor_invoices")
    issues += _check_numeric(po, PO_NUMERIC_COLS, "purchase_orders")

    # --- Referential integrity ---
    inv_vids = set(inv["vendor_id"].unique())
    po_vids = set(po["vendor_id"].unique())
    master_vids = set(vend["vendor_id"].unique())

    orphan_inv = inv_vids - master_vids
    if orphan_inv:
        issues.append(ValidationIssue("WARNING", "vendor_invoices",
            f"vendor_ids not in vendor master: {sorted(orphan_inv)[:5]}"))

    orphan_po = po_vids - master_vids
    if orphan_po:
        issues.append(ValidationIssue("WARNING", "purchase_orders",
            f"vendor_ids not in vendor master: {sorted(orphan_po)[:5]}"))

    # --- UOM inventory ---
    inv_uoms = set(inv["uom"].unique())
    po_uoms = set(po["uom"].unique())
    unexpected = (inv_uoms | po_uoms) - {"Nos", "Box(10)"}
    if unexpected:
        issues.append(ValidationIssue("WARNING", "uom",
            f"Unexpected UOM values found: {sorted(unexpected)}"))

    return LoadResult(
        invoices=inv,
        purchase_orders=po,
        vendors=vend,
        products=prod,
        issues=issues,
    )

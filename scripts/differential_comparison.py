"""
Generate differential comparison between starter classifier and new classifier.
Produces outputs/reconciliation_comparison.csv
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DATA_DIR = Path("data")

# --- Run starter classifier ---
inv = pd.read_csv(DATA_DIR / "vendor_invoices.csv")
po = pd.read_csv(DATA_DIR / "purchase_orders.csv").set_index("po_number")

def starter_classify(r):
    if r.po_number not in po.index:
        return "MISSING_PO"
    p = po.loc[r.po_number]
    if r.vendor_id != p.vendor_id:
        return "VENDOR_MISMATCH"
    if str(r.uom) != str(p.uom):
        return "UOM_MISMATCH"
    if r.qty != p.qty:
        return "QTY_MISMATCH"
    if abs(r.rate - p.rate) > 0.01:
        return "RATE_MISMATCH"
    if abs(r.gst_amount - round(r.taxable_value * 0.18, 2)) > 0.05:
        return "GST_ERROR"
    return "CLEAN"

inv_copy = inv.copy()
inv_copy["starter_status"] = inv_copy.apply(starter_classify, axis=1)

# Duplicate billing
clean = inv_copy[inv_copy.starter_status == "CLEAN"].sort_values("invoice_date")
dupes = clean[clean.duplicated(subset=["po_number"], keep="first")]
inv_copy.loc[dupes.index, "starter_status"] = "DUPLICATE_INVOICE"

starter = inv_copy[["invoice_number", "starter_status"]].copy()

# --- Load new classifier output ---
new = pd.read_csv("outputs/reconciliation_submission.csv")
new = new.rename(columns={"status": "new_status"})

# --- Merge ---
comparison = starter.merge(new, on="invoice_number", how="outer")
comparison["changed"] = comparison["starter_status"] != comparison["new_status"]
comparison["reason"] = ""

for idx, row in comparison[comparison["changed"]].iterrows():
    comparison.loc[idx, "reason"] = f"Starter={row['starter_status']}, New={row['new_status']}"

comparison.to_csv("outputs/reconciliation_comparison.csv", index=False)

# Summary
print("=" * 60)
print("DIFFERENTIAL COMPARISON: STARTER vs NEW")
print("=" * 60)
print(f"Total invoices: {len(comparison)}")
print(f"Changed: {comparison['changed'].sum()}")
print(f"Unchanged: {(~comparison['changed']).sum()}")
print()

if comparison["changed"].sum() > 0:
    print("Changed classifications:")
    for _, row in comparison[comparison["changed"]].iterrows():
        print(f"  {row['invoice_number']}: {row['starter_status']} -> {row['new_status']}")
else:
    print("No differences between starter and new classifier.")

print()
print("Starter distribution:")
print(starter["starter_status"].value_counts().to_string())
print()
print("New distribution:")
print(new["new_status"].value_counts().to_string())

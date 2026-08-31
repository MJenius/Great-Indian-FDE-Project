#!/usr/bin/env python3
"""Starter for the Reconciliation family. Runs as-is and beats the naive
baseline; the edges where records refuse to line up are yours to solve.
Any language or tool is equally legal — this file is one path, the output
format is the contract."""
import pandas as pd

inv = pd.read_csv("vendor_invoices.csv")
po = pd.read_csv("purchase_orders.csv").set_index("po_number")

def ask_model(prompt: str) -> str:
    """Wire this to whichever provider or local model you use — or delete
    it and orchestrate however you like."""
    raise NotImplementedError

def classify(r):
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

inv["status"] = inv.apply(classify, axis=1)

# Duplicate billing: multiple invoices against one PO — earliest stays, rest flagged.
clean = inv[inv.status == "CLEAN"].sort_values("invoice_date")
dupes = clean[clean.duplicated(subset=["po_number"], keep="first")]
inv.loc[dupes.index, "status"] = "DUPLICATE_INVOICE"

# The precedence order above is a choice, and it moves your macro-F1. Tune it.
# In scored sets, expect messier inputs than these practice files — that is
# where model calls stop being optional.

inv[["invoice_number", "status"]].to_csv("submission.csv", index=False)
print(inv.status.value_counts())

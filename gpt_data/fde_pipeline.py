#!/usr/bin/env python3
"""
Great Indian FDE Hiring Hackathon 2026
Local, repeatable DRI pipeline.

Usage:
  python fde_pipeline.py reconcile --data-dir .
  python fde_pipeline.py knowledge --data-dir .
  python fde_pipeline.py migration-plan --data-dir .
  python fde_pipeline.py all --data-dir .

Optional sandbox execution:
  DRI_BASE=https://<competition-origin>/api/public/sandbox/v1
  DRI_KEY=dri_...
  python fde_pipeline.py sandbox-w1
  python fde_pipeline.py sandbox-w2
  python fde_pipeline.py sandbox-w3
  python fde_pipeline.py sandbox-m1
  python fde_pipeline.py sandbox-m2
  python fde_pipeline.py sandbox-m3

The sandbox executor intentionally does not probe undocumented endpoints.
It uses only the endpoints documented by the competition.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import pandas as pd


STATUSES = [
    "CLEAN",
    "QTY_MISMATCH",
    "RATE_MISMATCH",
    "DUPLICATE_INVOICE",
    "MISSING_PO",
    "VENDOR_MISMATCH",
    "GST_ERROR",
    "UOM_MISMATCH",
]


def load_csv(data_dir: Path, name: str) -> pd.DataFrame:
    return pd.read_csv(data_dir / name)


def reconcile(data_dir: Path):
    inv = load_csv(data_dir, "vendor_invoices.csv")
    po = load_csv(data_dir, "purchase_orders.csv")

    # Exact PO reference first. This is the contract used by the starter kit.
    j = inv.merge(po, on="po_number", how="left", suffixes=("_inv", "_po"))

    missing = j["vendor_id_po"].isna()
    vendor = (~missing) & (j["vendor_id_inv"] != j["vendor_id_po"])
    uom = (~missing) & (
        j["uom_inv"].astype(str).str.strip() != j["uom_po"].astype(str).str.strip()
    )
    qty = (~missing) & (j["qty_inv"] != j["qty_po"])
    rate = (~missing) & ((j["rate_inv"] - j["rate_po"]).abs() > 0.01)
    gst_expected = (j["taxable_value"] * j["gst_rate_pct"] / 100).round(2)
    gst = ((j["gst_amount"] - gst_expected).abs() > 0.05)

    # Precedence is deliberate: it prevents UOM errors from becoming
    # simultaneous quantity/rate errors and matches the public starter.
    status = pd.Series("CLEAN", index=inv.index, dtype="object")
    for mask, label in [
        (missing, "MISSING_PO"),
        (vendor, "VENDOR_MISMATCH"),
        (uom, "UOM_MISMATCH"),
        (qty & ~uom, "QTY_MISMATCH"),
        (rate & ~uom & ~qty, "RATE_MISMATCH"),
        (gst & ~(missing | vendor | uom | qty | rate), "GST_ERROR"),
    ]:
        status.loc[mask] = label

    # Duplicate only among otherwise-clean invoices; earliest invoice wins.
    clean = status.eq("CLEAN")
    dup = clean & inv.duplicated("po_number", keep="first")
    status.loc[dup] = "DUPLICATE_INVOICE"

    submission = inv[["invoice_number"]].copy()
    submission["status"] = status.values

    # Diagnostics make the pipeline auditable.
    diag = inv[[
        "invoice_number", "invoice_date", "vendor_id", "vendor_name_on_invoice",
        "po_number", "sku", "uom", "qty", "rate", "taxable_value",
        "gst_rate_pct", "gst_amount", "invoice_total"
    ]].copy()
    diag["status"] = status.values
    diag["raw_qty_mismatch"] = qty.values
    diag["raw_rate_mismatch"] = rate.values
    diag["raw_uom_mismatch"] = uom.values
    diag["raw_vendor_mismatch"] = vendor.values
    diag["raw_missing_po"] = missing.values
    diag["raw_gst_error"] = gst.values

    return submission, diag


def normalize_customer_name(s: str) -> str:
    s = str(s).upper().strip()
    # Treat the known branch/copy suffixes as non-identity-bearing.
    s = re.sub(r"\s*\((?:SOUTH|NORTH|II)\)\s*$", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s


def migration_plan(data_dir: Path):
    products = load_csv(data_dir, "products.csv")
    customers = load_csv(data_dir, "customers.csv")

    # M1: update only products that have a 2023 price.
    m1 = products.loc[products["list_price_2023"].notna(),
                      ["sku", "list_price_2023"]].copy()
    m1["action"] = "PATCH"
    m1["drishti_price"] = m1["list_price_2023"]
    m1 = m1[["sku", "action", "drishti_price"]]

    # M2: FlowTech -> DRI mapping.
    base = products[~products["sku"].astype(str).str.startswith("FT-")].copy()
    m2 = []
    for _, row in products[products["sku"].astype(str).str.startswith("FT-")].iterrows():
        desc = str(row["description"])
        # Remove one or more repeated FlowTech suffixes.
        clean_desc = re.sub(r"(?:\s*\(FlowTech\))+$", "", desc).strip()

        candidates = base[
            (base["description"].astype(str).str.strip() == clean_desc)
            & (
                base["list_price_2023"].fillna(-1)
                == (row["list_price_2023"] if pd.notna(row["list_price_2023"]) else -1)
            )
        ]

        if pd.isna(row["list_price_2023"]) or len(candidates) != 1:
            m2.append({
                "flowtech_sku": row["sku"],
                "action": "REVIEW",
                "reason": (
                    "No 2023 price" if pd.isna(row["list_price_2023"])
                    else f"Expected exactly one match, found {len(candidates)}"
                ),
            })
        else:
            m2.append({
                "flowtech_sku": row["sku"],
                "action": "PATCH",
                "mapped_dri_sku": candidates.iloc[0]["sku"],
            })

    # W3: duplicate customer -> earliest legacy record in each normalized group.
    customers = customers.copy()
    customers["_norm"] = customers["customer_name"].map(normalize_customer_name)
    merges = []
    for _, group in customers.groupby("_norm", sort=False):
        if len(group) <= 1:
            continue
        original = group.iloc[0]["legacy_id"]
        for _, dup in group.iloc[1:].iterrows():
            merges.append({
                "legacy_id": dup["legacy_id"],
                "merged_into": original,
                "customer_name": dup["customer_name"],
            })

    # M3: deterministic unique IDs for customers still unmigrated.
    existing = set(customers["crm_id"].dropna().astype(str))
    next_id = 1
    m3 = []
    for _, row in customers[customers["migrated_to_salestrack"].astype(str).eq("N")].iterrows():
        while f"ST-{next_id:05d}" in existing:
            next_id += 1
        new_id = f"ST-{next_id:05d}"
        existing.add(new_id)
        m3.append({
            "legacy_id": row["legacy_id"],
            "crm_id": new_id,
            "action": "PATCH",
        })
        next_id += 1

    return {
        "M1_price_updates": m1.to_dict("records"),
        "M2_flowtech_mapping": m2,
        "W3_customer_merges": merges,
        "M3_salestrack_updates": m3,
    }


def answer_knowledge_question(question: str, today="2026-08-31"):
    """
    Deterministic policy engine for the four provided policy documents.
    It is deliberately conservative: if a question doesn't match a known
    policy family, it returns NEEDS_REVIEW rather than inventing an answer.
    """
    q = question.lower()
    amount_match = re.search(r"(?:rs\.?|₹)\s*([\d,]+(?:\.\d+)?)", q)
    amount = float(amount_match.group(1).replace(",", "")) if amount_match else None

    # Pricing policy: determine governing version from transaction date.
    year_match = re.search(r"\b(20\d{2})\b", q)
    year = int(year_match.group(1)) if year_match else 2026
    modern = year >= 2023
    pricing_source = "PP-2023" if modern else "PP-2019"

    if "discount" in q and amount is not None:
        if modern:
            pct = 0 if amount < 500000 else 10 if amount <= 1500000 else 14
        else:
            pct = 0 if amount < 100000 else 6 if amount <= 500000 else 12
        return f"{pct}%", pricing_source

    if "credit" in q:
        if "platinum" in q:
            return "60 days", "PP-2023"
        # PP-2023 standard is 30 days; Gold is not given a special extension.
        if "gold" in q or "standard" in q or "today" in q:
            return "30 days", "PP-2023"
        return "30 days", "PP-2023"

    if "freight" in q:
        if modern:
            return "Buyer bears freight; all despatches are ex-works.", "PP-2023"
        if amount is not None and amount > 200000:
            return "DRI bears freight; despatch is FOR destination.", "PP-2019"
        return "Freight-to-pay; buyer bears freight.", "PP-2019"

    if "warranty" in q:
        # Specific date arithmetic beats a generic warranty statement.
        dispatch = re.search(r"despatch(?:ed)?\s+(?:in\s+)?([A-Za-z]+)\s+(20\d{2})", q)
        commissioned = re.search(r"commissioned\s+(?:in\s+)?([A-Za-z]+)\s+(20\d{2})", q)
        if dispatch and commissioned:
            import calendar
            from datetime import date
            from dateutil.relativedelta import relativedelta
            dm = list(calendar.month_name).index(dispatch.group(1).capitalize())
            cm = list(calendar.month_name).index(commissioned.group(1).capitalize())
            d = date(int(dispatch.group(2)), dm, 1)
            c = date(int(commissioned.group(2)), cm, 1)
            end = min(d + relativedelta(months=18), c + relativedelta(months=12))
            return end.strftime("%B %Y"), "WRP-2020"
        if "flowtech" in q:
            return (
                "24 months from dispatch for FlowTech products from pre-acquisition stock, "
                "until existing stock is exhausted.",
                "WRP-2020",
            )
        return (
            "18 months from dispatch or 12 months from commissioning, whichever is earlier.",
            "WRP-2020",
        )

    if "document" in q and ("vendor" in q or "onboard" in q):
        return (
            "GST registration certificate, cancelled cheque, and MSME declaration where applicable.",
            "VOS-7",
        )

    if "trial" in q and ("purchase" in q or "po" in q or "order" in q):
        return "Rs 2,00,000", "VOS-7"

    if "approval" in q or "approv" in q:
        if amount is not None and amount > 1000000:
            if "direct" in q or "casting" in q:
                return "CFO, Plant Head, and QA.", "VOS-7"
            return "CFO.", "VOS-7"
        return "GM Procurement.", "VOS-7"

    if "restocking" in q or "return" in q:
        return "10% of invoice value.", "WRP-2020"

    if "notice" in q and ("price" in q or "list" in q or "revision" in q):
        return "15 days.", "PP-2023"

    if "end" in q and "warranty" in q:
        return (
            "The earlier of 18 months from dispatch or 12 months from commissioning.",
            "WRP-2020",
        )

    return "NEEDS_REVIEW", "UNKNOWN"


def knowledge(data_dir: Path):
    q = load_csv(data_dir, "knowledge_questions.csv")
    rows = []
    for _, r in q.iterrows():
        ans, src = answer_knowledge_question(str(r["question"]))
        rows.append({"qid": r["qid"], "answer": ans, "governing_source": src})
    return pd.DataFrame(rows)


class Sandbox:
    def __init__(self, base: str, key: str, min_interval=1.05):
        import requests
        self.requests = requests
        self.base = base.rstrip("/")
        self.headers = {"Authorization": f"Bearer {key}"}
        self.min_interval = min_interval
        self.last = 0.0

    def call(self, method, path, payload=None):
        wait = self.min_interval - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait)
        url = self.base + path
        if method == "GET":
            r = self.requests.get(url, headers=self.headers, timeout=30)
        elif method == "POST":
            r = self.requests.post(url, headers={**self.headers, "Content-Type": "application/json"},
                                    json=payload, timeout=30)
        elif method == "PATCH":
            r = self.requests.patch(url, headers={**self.headers, "Content-Type": "application/json"},
                                    json=payload, timeout=30)
        else:
            raise ValueError(method)
        self.last = time.time()
        r.raise_for_status()
        return r.json()

    def get(self, path):
        return self.call("GET", path)

    def post(self, path, payload):
        return self.call("POST", path, payload)

    def patch(self, path, payload):
        return self.call("PATCH", path, payload)


def sandbox_from_env():
    base = os.environ.get("DRI_BASE")
    key = os.environ.get("DRI_KEY")
    if not base or not key:
        raise SystemExit("Set DRI_BASE and DRI_KEY first.")
    return Sandbox(base, key)


def run_w1(sb: Sandbox):
    # Exact public brief: Sri Ranga Castings, Coimbatore, TN,
    # GSTIN, MSME/direct-material flags, projected spend 14L.
    vendor = sb.post("/erp/vendors", {
        "vendor_name": "Sri Ranga Castings",
        "gstin": "33AAACS1234R1ZK",
        "city": "Coimbatore",
        "state": "TN",
        "msme_registered": "Y",
        "gst_cert": True,
        "cancelled_cheque": True,
        "msme_declaration": True,
        "direct_material": True,
        "trial_po_cap": 200000,
    })
    # Public task requires CFO + Plant Head + QA.
    for role in ("CFO", "PLANT_HEAD", "QA"):
        sb.post("/erp/approvals", {"vendor_name": "Sri Ranga Castings", "role": role})
    return vendor


def run_w2(sb: Sandbox):
    invoices = pd.DataFrame(sb.get("/erp/invoices"))
    pos = pd.DataFrame(sb.get("/erp/purchase_orders"))
    # Reuse the same precedence as local reconciliation.
    tmp_dir = Path(".fde_sandbox_tmp")
    tmp_dir.mkdir(exist_ok=True)
    invoices.to_csv(tmp_dir / "vendor_invoices.csv", index=False)
    pos.to_csv(tmp_dir / "purchase_orders.csv", index=False)
    sub, _ = reconcile(tmp_dir)
    merged = invoices.merge(pos, on="po_number", how="left", suffixes=("_inv", "_po"))
    totals = sub["status"].value_counts().to_dict()
    exceptions = {k: int(v) for k, v in totals.items() if k != "CLEAN"}
    value_at_risk = float(
        invoices.loc[sub["status"].ne("CLEAN"), "invoice_total"].sum()
    )
    payload = {"counts": exceptions, "value_at_risk": round(value_at_risk, 2)}
    return sb.post("/erp/reports/exceptions", payload)


def run_w3(sb: Sandbox):
    customers = pd.DataFrame(sb.get("/crm/customers"))
    customers["_norm"] = customers["customer_name"].map(normalize_customer_name)
    actions = []
    for _, group in customers.groupby("_norm", sort=False):
        if len(group) <= 1:
            continue
        original = group.iloc[0]["legacy_id"]
        for _, dup in group.iloc[1:].iterrows():
            sb.patch(f"/crm/customers/{dup['legacy_id']}",
                     {"merged_into": original})
            actions.append((dup["legacy_id"], original))
    return actions


def run_m1(sb: Sandbox):
    products = pd.DataFrame(sb.get("/erp/products"))
    actions = []
    for _, r in products[products["list_price_2023"].notna()].iterrows():
        sb.patch(f"/erp/products/{r['sku']}",
                 {"drishti_price": float(r["list_price_2023"])})
        actions.append(r["sku"])
    return actions


def run_m2(sb: Sandbox):
    products = pd.DataFrame(sb.get("/erp/products"))
    base = products[~products["sku"].astype(str).str.startswith("FT-")]
    actions = []
    for _, r in products[products["sku"].astype(str).str.startswith("FT-")].iterrows():
        if pd.isna(r["list_price_2023"]):
            continue
        desc = re.sub(r"(?:\s*\(FlowTech\))+$", "", str(r["description"])).strip()
        candidates = base[
            (base["description"].astype(str).str.strip() == desc)
            & (base["list_price_2023"] == r["list_price_2023"])
        ]
        if len(candidates) == 1:
            sb.patch(f"/erp/products/{r['sku']}",
                     {"mapped_dri_sku": candidates.iloc[0]["sku"]})
            actions.append((r["sku"], candidates.iloc[0]["sku"]))
    return actions


def run_m3(sb: Sandbox):
    customers = pd.DataFrame(sb.get("/crm/customers"))
    existing = set(customers["crm_id"].dropna().astype(str))
    next_id = 1
    actions = []
    for _, r in customers[customers["migrated_to_salestrack"].astype(str).eq("N")].iterrows():
        while f"ST-{next_id:05d}" in existing:
            next_id += 1
        new_id = f"ST-{next_id:05d}"
        existing.add(new_id)
        sb.patch(f"/crm/customers/{r['legacy_id']}",
                 {"migrated_to_salestrack": "Y", "crm_id": new_id})
        actions.append((r["legacy_id"], new_id))
        next_id += 1
    return actions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=[
        "reconcile", "knowledge", "migration-plan", "all",
        "sandbox-w1", "sandbox-w2", "sandbox-w3", "sandbox-m1",
        "sandbox-m2", "sandbox-m3",
    ])
    ap.add_argument("--data-dir", default=".")
    ap.add_argument("--out-dir", default="fde_output")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(exist_ok=True)

    if args.command in ("reconcile", "all"):
        sub, diag = reconcile(data_dir)
        sub.to_csv(out_dir / "reconciliation_submission.csv", index=False)
        diag.to_csv(out_dir / "reconciliation_diagnostics.csv", index=False)
        print(sub["status"].value_counts().to_string())

    if args.command in ("knowledge", "all"):
        k = knowledge(data_dir)
        k.to_csv(out_dir / "knowledge_submission.csv", index=False)
        print(k.to_string(index=False))

    if args.command in ("migration-plan", "all"):
        plan = migration_plan(data_dir)
        (out_dir / "migration_plan.json").write_text(
            json.dumps(plan, indent=2), encoding="utf-8"
        )
        print("M1 updates:", len(plan["M1_price_updates"]))
        print("M2 mappings:", sum(x["action"] == "PATCH" for x in plan["M2_flowtech_mapping"]))
        print("M2 reviews:", sum(x["action"] == "REVIEW" for x in plan["M2_flowtech_mapping"]))
        print("W3 merges:", len(plan["W3_customer_merges"]))
        print("M3 updates:", len(plan["M3_salestrack_updates"]))

    if args.command.startswith("sandbox-"):
        sb = sandbox_from_env()
        fn = {
            "sandbox-w1": run_w1,
            "sandbox-w2": run_w2,
            "sandbox-w3": run_w3,
            "sandbox-m1": run_m1,
            "sandbox-m2": run_m2,
            "sandbox-m3": run_m3,
        }[args.command]
        result = fn(sb)
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()

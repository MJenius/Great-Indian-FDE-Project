import os
import json
import re
import requests
import pandas as pd

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")
H = {"Authorization": f"Bearer {KEY}"}

def normalize_name(name: str) -> str:
    if not name:
        return ""
    s = str(name).upper()
    s = re.sub(r"[&]", " AND ", s)
    s = re.sub(r"\b(PVT\.?|LTD\.?|PRIVATE|LIMITED|CO\.?|COMPANY|ENTERPRISES?|TRADERS?|AGENCIES|AGENCY|ASSOCIATES|DISTRIBUTORS?)\b", " ", s)
    s = re.sub(r"[^A-Z0-9]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def analyze_w3():
    r = requests.get(BASE + "/crm/customers", headers=H)
    r.raise_for_status()
    customers = r.json()["customers"]

    df = pd.DataFrame(customers)
    print(f"Total customers fetched from live sandbox: {len(df)}")
    print("Schema Columns:", df.columns.tolist())

    df["norm_name"] = df["customer_name"].apply(normalize_name)
    
    # Also inspect region
    groups = {}
    for _, row in df.iterrows():
        norm_n = row["norm_name"]
        region = str(row.get("region", "")).strip().upper()
        key = f"NAME:{norm_n} | REGION:{region}"
        groups.setdefault(key, []).append(row.to_dict())

    print(f"Total unique corporate identity groups: {len(groups)}")
    
    duplicates = []
    originals = []
    
    print("\n" + "=" * 100)
    print(f"{'GROUP IDENTITY KEY':<45} | {'ORIGINAL':<12} | {'DUPLICATES (PATCH merged_into)':<35}")
    print("=" * 100)
    
    for key, members in sorted(groups.items()):
        # Sort members by legacy_id numerically/alphabetically (earliest is original)
        members_sorted = sorted(members, key=lambda x: str(x.get("legacy_id")))
        orig = members_sorted[0]
        dups = members_sorted[1:]
        
        originals.append(orig)
        for d in dups:
            duplicates.append({
                "duplicate_legacy_id": d["legacy_id"],
                "duplicate_name": d["customer_name"],
                "original_legacy_id": orig["legacy_id"],
                "original_name": orig["customer_name"],
            })
        
        dup_str = ", ".join([f"{d['legacy_id']} ({d['customer_name']})" for d in dups])
        if dups:
            print(f"{key:<45} | {orig['legacy_id']} | {dup_str}")

    print("\n" + "=" * 100)
    print(f"TOTAL ORIGINAL ACCOUNTS (40 Expected): {len(originals)}")
    print(f"TOTAL DUPLICATE ACCOUNTS TO PATCH (45 Expected): {len(duplicates)}")
    print("=" * 100)

    # Save to CSV for full audit inspection
    pd.DataFrame(duplicates).to_csv("outputs/live_customer_duplicate_mapping.csv", index=False)
    print("Saved live mapping to outputs/live_customer_duplicate_mapping.csv")

if __name__ == "__main__":
    analyze_w3()

import os
import requests

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")
H = {"Authorization": f"Bearer {KEY}"}

def verify_m3():
    customers = requests.get(BASE + "/crm/customers", headers=H).json()["customers"]

    pending = [c for c in customers if c.get("migrated_to_salestrack") != "Y"]
    ids = [c.get("crm_id") for c in customers]

    print("=" * 60)
    print("M3 LIVE SANDBOX VERIFICATION:")
    print("=" * 60)
    print("Total:", len(customers))
    print("Still N:", len(pending))
    print("Unique CRM IDs:", len(set(ids)))
    print("Missing CRM IDs:", sum(c.get("crm_id") in (None, "") for c in customers))

    print("\nNewly migrated accounts (C-50xx):")
    migrated_new = [c for c in customers if c.get("legacy_id", "").startswith("C-50") and c.get("migrated_to_salestrack") == "Y"]
    for c in sorted(migrated_new, key=lambda x: x["legacy_id"]):
        print(f"{c['legacy_id']}: {c.get('crm_id')}")

if __name__ == "__main__":
    verify_m3()

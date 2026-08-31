import os
import requests

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")
H = {"Authorization": f"Bearer {KEY}"}

def check_m3():
    r = requests.get(BASE + "/crm/customers", headers=H)
    r.raise_for_status()
    customers = r.json()["customers"]

    print("Total customers:", len(customers))

    existing = []
    pending = []

    for c in customers:
        if c.get("migrated_to_salestrack") == "Y":
            existing.append(c.get("crm_id"))
        else:
            pending.append(c)

    print("Already migrated:", len(existing))
    print("Not migrated:", len(pending))

    print("\nExisting CRM IDs:")
    for x in sorted(existing, key=lambda s: str(s)):
        print(x)

    print("\nPending customers:")
    for c in sorted(pending, key=lambda x: str(x.get("legacy_id"))):
        print(c.get("legacy_id"), "|", c.get("name"), "|", c.get("migrated_to_salestrack"), "|", c.get("crm_id"))

if __name__ == "__main__":
    check_m3()

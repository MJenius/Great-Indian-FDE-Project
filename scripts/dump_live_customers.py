import os
import json
import requests

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")
H = {"Authorization": f"Bearer {KEY}"}

def dump_customers():
    r = requests.get(BASE + "/crm/customers", headers=H)
    r.raise_for_status()
    customers = r.json()["customers"]

    print("TOTAL CUSTOMERS:", len(customers))
    print("=" * 100)
    for c in sorted(customers, key=lambda x: x["legacy_id"]):
        print(
            f"{c['legacy_id']:<8} | "
            f"{c.get('customer_name',''):<40} | "
            f"tier={c.get('tier',''):<10} | "
            f"reg={c.get('region',''):<6} | "
            f"mig={c.get('migrated_to_salestrack',''):<2} | "
            f"crm_id={c.get('crm_id',''):<10} | "
            f"merged_into={repr(c.get('merged_into'))}"
        )

if __name__ == "__main__":
    dump_customers()

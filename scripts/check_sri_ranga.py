import os
import json
import requests

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")
H = {"Authorization": f"Bearer {KEY}"}

def check_sri_ranga():
    r = requests.get(BASE + "/erp/vendors", headers=H)
    r.raise_for_status()
    vendors = r.json()["vendors"]

    print("Total existing vendors in sandbox:", len(vendors))
    ranga = [v for v in vendors if "RANGA" in v.get("vendor_name", "").upper() or "33AAACS1234R1ZK" in v.get("gstin", "")]
    print("Sri Ranga present?:", len(ranga) > 0)
    if ranga:
        print("Existing Sri Ranga record:", json.dumps(ranga[0], indent=2))

    # Also check /erp/approvals if endpoint exists
    try:
        r_app = requests.get(BASE + "/erp/approvals", headers=H)
        if r_app.status_code == 200:
            print("Approvals endpoint exists, count:", len(r_app.json().get("approvals", [])))
    except Exception as e:
        print("Approvals GET not available or empty:", e)

if __name__ == "__main__":
    check_sri_ranga()

import os
import json
import requests

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")
H = {"Authorization": f"Bearer {KEY}"}

def check_endpoints():
    for endpoint in ["/erp/approvals", "/erp/vendors"]:
        try:
            r = requests.get(BASE + endpoint, headers=H)
            print(f"\n=== {endpoint} === HTTP {r.status_code}")
            print(json.dumps(r.json(), indent=2))
        except Exception as e:
            print(f"\n=== {endpoint} === Error: {e}")

if __name__ == "__main__":
    check_endpoints()

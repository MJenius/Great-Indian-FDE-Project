import os
import requests
import time

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

def post_approvals():
    vendor_name = "Sri Ranga Castings"
    # CFO was created during probe (HTTP 201). Now post PLANT_HEAD and QA, and re-post CFO if needed.
    for role in ["CFO", "PLANT_HEAD", "QA"]:
        r = requests.post(BASE + "/erp/approvals", headers=H, json={"vendor_name": vendor_name, "role": role})
        print(f"Role {role} -> HTTP {r.status_code}: {r.text}")
        time.sleep(1.1)

if __name__ == "__main__":
    post_approvals()

import os
import requests
import time

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")

H = {
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
}

vendor_id = "V-1061"

def main():
    print(f"Creating W1 approvals for vendor {vendor_id}...")
    for role in ["CFO", "Plant Head", "QA"]:
        r = requests.post(
            BASE + "/erp/approvals",
            headers=H,
            json={
                "vendor_id": vendor_id,
                "approver_role": role,
            },
        )

        print(role, r.status_code, r.text)
        r.raise_for_status()
        time.sleep(1.1)

    print("W1 approvals complete.")

if __name__ == "__main__":
    main()

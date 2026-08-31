import os
import json
import requests

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")

H = {
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
}

payload = {
    "vendor_name": "Sri Ranga Castings",
    "gstin": "33AAACS1234R1ZK",
    "city": "Coimbatore",
    "state": "TN",
    "payment_terms_days": 30,
    "msme_registered": "Y",
    "source_system": "DRISHTI",
    "gst_cert": True,
    "cancelled_cheque": True,
    "msme_declaration": True,
    "trial_po_cap": 200000.00,
    "direct_material": True,
}

def main():
    r = requests.post(
        BASE + "/erp/vendors",
        headers=H,
        json=payload,
    )

    print("HTTP:", r.status_code)
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)
    r.raise_for_status()

if __name__ == "__main__":
    main()

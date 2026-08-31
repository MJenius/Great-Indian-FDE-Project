import os
import requests

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")

H = {
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
}

payload = {
    "counts": {
        "MISSING_PO": 12,
        "VENDOR_MISMATCH": 12,
        "UOM_MISMATCH": 13,
        "QTY_MISMATCH": 21,
        "RATE_MISMATCH": 16,
        "GST_ERROR": 16,
        "DUPLICATE_INVOICE": 5,
    },
    "value_at_risk": 88404135.42,
}

def main():
    r = requests.post(
        BASE + "/erp/reports/exceptions",
        headers=H,
        json=payload,
    )

    print("HTTP:", r.status_code)
    print(r.text)
    r.raise_for_status()

if __name__ == "__main__":
    main()

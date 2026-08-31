import os
import requests

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")
H = {"Authorization": f"Bearer {KEY}"}

def check_reports():
    for path in ["/erp/reports/exceptions", "/erp/reports"]:
        try:
            r = requests.get(BASE + path, headers=H)
            print(f"\n=== {path} === HTTP {r.status_code}")
            print(r.text)
        except Exception as e:
            print(f"\n=== {path} === Error: {e}")

if __name__ == "__main__":
    check_reports()

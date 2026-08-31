import os
import json
import requests

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")
H = {"Authorization": f"Bearer {KEY}"}

def query_vendors():
    r = requests.get(BASE + "/erp/vendors", headers=H)
    r.raise_for_status()
    data = r.json()
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    query_vendors()

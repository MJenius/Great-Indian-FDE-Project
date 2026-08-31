import os
import requests
import json

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

# Probe with vendor_name only to see what next field is required
r = requests.post(BASE + "/erp/approvals", headers=H, json={"vendor_name": "Sri Ranga Castings"})
print("vendor_name only response:", r.status_code, r.text)

# Probe with vendor_name + role / approver / approval_type
for candidate in ["role", "approver", "approval", "approved_by", "signoff", "approval_type"]:
    r = requests.post(BASE + "/erp/approvals", headers=H, json={"vendor_name": "Sri Ranga Castings", candidate: "CFO"})
    print(f"Candidate '{candidate}' -> {r.status_code}: {r.text}")

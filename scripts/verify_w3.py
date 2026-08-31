import os
import requests

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")
H = {"Authorization": f"Bearer {KEY}"}

mapping = {
    "C-5041": "C-5001", "C-5042": "C-5002", "C-5043": "C-5003", "C-5044": "C-5004",
    "C-5045": "C-5005", "C-5046": "C-5006", "C-5047": "C-5007", "C-5048": "C-5008",
    "C-5049": "C-5009", "C-5050": "C-5010", "C-5051": "C-5011", "C-5052": "C-5012",
    "C-5053": "C-5013", "C-5054": "C-5014", "C-5055": "C-5015", "C-5056": "C-5016",
    "C-5057": "C-5017", "C-5058": "C-5018", "C-5059": "C-5019", "C-5060": "C-5020",
    "C-5061": "C-5021", "C-5062": "C-5022", "C-5063": "C-5023", "C-5064": "C-5024",
    "C-5065": "C-5025", "C-5066": "C-5026", "C-5067": "C-5027", "C-5068": "C-5028",
    "C-5069": "C-5029", "C-5070": "C-5030", "C-5071": "C-5031", "C-5072": "C-5032",
    "C-5073": "C-5033", "C-5074": "C-5034", "C-5075": "C-5035", "C-5076": "C-5036",
    "C-5077": "C-5037", "C-5078": "C-5038", "C-5079": "C-5039", "C-5080": "C-5040",
    "C-5081": "C-5024", "C-5082": "C-5014", "C-5083": "C-5019", "C-5084": "C-5020",
    "C-5085": "C-5029",
}

def verify_w3():
    customers = requests.get(f"{BASE}/crm/customers", headers=H).json()["customers"]
    by_id = {c["legacy_id"]: c for c in customers}
    
    errors = []
    
    # Check all 45 duplicates
    for dup, original in mapping.items():
        actual = by_id[dup].get("merged_into")
        if actual != original:
            errors.append(f"{dup}: expected merged_into={original}, got {actual}")
            
    # Check all 40 originals are untouched
    for original in [f"C-{5001+i}" for i in range(40)]:
        actual = by_id[original].get("merged_into")
        if actual not in (None, ""):
            errors.append(f"{original}: original account modified! merged_into={actual}")

    print("=" * 60)
    print("W3 LIVE SANDBOX VERIFICATION:")
    print("=" * 60)
    print("Total customers:", len(customers))
    print("W3 duplicate mappings checked:", len(mapping))
    print("Errors found:", len(errors))
    
    for e in errors:
        print("ERROR:", e)
        
    if not errors:
        print("\n>>> [PASS] W3 VERIFICATION: 100% SUCCESSFUL <<<")

if __name__ == "__main__":
    verify_w3()

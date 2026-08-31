import os
import time
import requests

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")

H = {
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
}

mapping = {
    "C-5041": "C-5001",
    "C-5042": "C-5002",
    "C-5043": "C-5003",
    "C-5044": "C-5004",
    "C-5045": "C-5005",
    "C-5046": "C-5006",
    "C-5047": "C-5007",
    "C-5048": "C-5008",
    "C-5049": "C-5009",
    "C-5050": "C-5010",
    "C-5051": "C-5011",
    "C-5052": "C-5012",
    "C-5053": "C-5013",
    "C-5054": "C-5014",
    "C-5055": "C-5015",
    "C-5056": "C-5016",
    "C-5057": "C-5017",
    "C-5058": "C-5018",
    "C-5059": "C-5019",
    "C-5060": "C-5020",
    "C-5061": "C-5021",
    "C-5062": "C-5022",
    "C-5063": "C-5023",
    "C-5064": "C-5024",
    "C-5065": "C-5025",
    "C-5066": "C-5026",
    "C-5067": "C-5027",
    "C-5068": "C-5028",
    "C-5069": "C-5029",
    "C-5070": "C-5030",
    "C-5071": "C-5031",
    "C-5072": "C-5032",
    "C-5073": "C-5033",
    "C-5074": "C-5034",
    "C-5075": "C-5035",
    "C-5076": "C-5036",
    "C-5077": "C-5037",
    "C-5078": "C-5038",
    "C-5079": "C-5039",
    "C-5080": "C-5040",
    "C-5081": "C-5024",
    "C-5082": "C-5014",
    "C-5083": "C-5019",
    "C-5084": "C-5020",
    "C-5085": "C-5029",
}

def main():
    print(f"Starting W3 distributor deduplication ({len(mapping)} patches) on live sandbox...")
    for i, (duplicate, original) in enumerate(mapping.items(), start=1):
        url = f"{BASE}/crm/customers/{duplicate}"
        
        for attempt in range(5):
            r = requests.patch(url, headers=H, json={"merged_into": original})
            if r.status_code == 429:
                wait = 2 ** attempt
                print(f"Rate limited on {duplicate}; waiting {wait}s...")
                time.sleep(wait)
                continue
            
            if r.status_code not in (200, 204):
                print(f"FAILED {duplicate} -> {original}: {r.status_code} {r.text}")
                raise SystemExit(1)
            
            print(f"[{i:02d}/45] PASS  {duplicate} -> {original}")
            break

        time.sleep(1.1)

    print(f"\nCompleted {len(mapping)} W3 patches.")

if __name__ == "__main__":
    main()

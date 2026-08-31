import os
import requests

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")
headers = {"Authorization": f"Bearer {KEY}"}

def check_live_fts():
    products = requests.get(f"{BASE}/erp/products", headers=headers).json()["products"]
    fts = [p for p in products if p["sku"].startswith("FT-")]

    print("=" * 80)
    print("CURRENT LIVE FLOWTECH MAPPINGS & PRICES:")
    print("=" * 80)
    for p in sorted(fts, key=lambda x: x["sku"]):
        sku = p["sku"]
        mapped = str(p.get("mapped_dri_sku"))
        d_price = str(p.get("drishti_price"))
        l_price = str(p.get("list_price_2023"))
        print(f"{sku:<8} | mapped_dri_sku: {mapped:<10} | drishti_price: {d_price:<10} | 2023_price: {l_price}")

if __name__ == "__main__":
    check_live_fts()

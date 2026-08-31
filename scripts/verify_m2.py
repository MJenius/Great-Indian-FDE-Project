import requests

BASE = "https://machinehack.com/api/public/sandbox/v1"
KEY = "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703"
headers = {"Authorization": f"Bearer {KEY}"}

def verify_m2():
    products = requests.get(f"{BASE}/erp/products", headers=headers).json()["products"]
    fts = [p for p in products if p["sku"].startswith("FT-")]
    
    print("=" * 60)
    print("FLOWTECH PRODUCTS LIVE VERIFICATION:")
    print("=" * 60)
    for p in sorted(fts, key=lambda x: x["sku"]):
        sku = p["sku"]
        mapped = p.get("mapped_dri_sku")
        price = p.get("list_price_2023")
        print(f"{sku}: mapped_dri_sku = {repr(mapped)} | list_price_2023 = {price}")

if __name__ == "__main__":
    verify_m2()

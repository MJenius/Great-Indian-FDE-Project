import os
import time
import requests

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")

HEADERS = {
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
}

MAPPINGS = {
    "FT-1400": "CP-160",
    "FT-1407": "CP-163",
    "FT-1414": "CP-107",
    "FT-1421": "CP-172",
    "FT-1428": "SM-127",
    "FT-1435": "CP-111",
    "FT-1449": "CP-122",
    "FT-1456": "SM-135",
    "FT-1463": "SM-108",
    "FT-1470": "CP-172",
    "FT-1477": "SM-139",
}

def main():
    print("Starting M2 FlowTech SKU mapping on live sandbox...")
    for ft_sku, dri_sku in MAPPINGS.items():
        url = f"{BASE}/erp/products/{ft_sku}"

        for attempt in range(5):
            r = requests.patch(
                url,
                headers=HEADERS,
                json={"mapped_dri_sku": dri_sku},
            )

            if r.status_code == 429:
                wait = 2 ** attempt
                print(f"Rate limited on {ft_sku}; waiting {wait}s...")
                time.sleep(wait)
                continue

            r.raise_for_status()
            print(f"{ft_sku} -> {dri_sku} [OK]")
            break

        time.sleep(1.1)

    print("M2 complete.")

if __name__ == "__main__":
    main()

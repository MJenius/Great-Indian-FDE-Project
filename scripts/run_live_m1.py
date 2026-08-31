import os
import requests
import time

BASE = "https://machinehack.com/api/public/sandbox/v1"
KEY = os.environ.get("DRI_KEY", "")
HEADERS = {
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
}

def request_with_retry(method, url, json_payload=None, max_retries=10, delay=1.1):
    for attempt in range(max_retries):
        try:
            if method == "GET":
                r = requests.get(url, headers=HEADERS, timeout=15)
            elif method == "PATCH":
                r = requests.patch(url, headers=HEADERS, json=json_payload, timeout=15)
            elif method == "POST":
                r = requests.post(url, headers=HEADERS, json=json_payload, timeout=15)
            else:
                raise ValueError(f"Unsupported method: {method}")

            if r.status_code == 429:
                wait_time = float(r.headers.get("Retry-After", 2.0 * (attempt + 1)))
                print(f"[429 Rate Limit] Backing off for {wait_time:.2f}s (Attempt {attempt+1}/{max_retries})...")
                time.sleep(wait_time)
                continue
            
            r.raise_for_status()
            time.sleep(delay)  # strict pacing: 1.1s = ~54 req/min (< 60 cap)
            return r.json()
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            print(f"[Request Error: {e}] Retrying in 2.0s...")
            time.sleep(2.0)

def main():
    print("Fetching current products from sandbox...")
    res = request_with_retry("GET", f"{BASE}/erp/products")
    products = res["products"]
    print(f"Total products in sandbox: {len(products)}")

    m1_eligible = [p for p in products if p["list_price_2023"] is not None]
    print(f"Total products eligible for M1 (non-null 2023 price): {len(m1_eligible)}")

    m1_updated = 0
    m1_already_matched = 0

    for i, p in enumerate(m1_eligible):
        sku = p["sku"]
        target_price = p["list_price_2023"]
        current_price = p.get("drishti_price")

        if current_price == target_price:
            m1_already_matched += 1
            continue

        request_with_retry("PATCH", f"{BASE}/erp/products/{sku}", json_payload={"drishti_price": target_price})
        m1_updated += 1
        if m1_updated % 10 == 0 or (m1_updated + m1_already_matched) == len(m1_eligible):
            print(f"Progress: {m1_updated + m1_already_matched}/{len(m1_eligible)} checked (Newly patched: {m1_updated}, Already matching: {m1_already_matched})")

    print("=" * 60)
    print(f"M1 COMPLETE! Total eligible: {len(m1_eligible)}, Patched: {m1_updated}, Already matched: {m1_already_matched}")
    print("=" * 60)

if __name__ == "__main__":
    main()

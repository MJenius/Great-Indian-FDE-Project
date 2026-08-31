import os
import time
import requests

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")

H = {
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
}

pending = [
    "C-5001", "C-5002", "C-5009", "C-5010", "C-5013",
    "C-5014", "C-5019", "C-5022", "C-5024", "C-5031",
    "C-5032", "C-5033", "C-5034", "C-5035", "C-5040",
    "C-5042", "C-5043", "C-5044", "C-5045", "C-5049",
    "C-5054", "C-5055", "C-5061", "C-5062", "C-5064",
    "C-5065", "C-5073", "C-5074", "C-5076", "C-5078",
]

assert len(pending) == 30

def main():
    print("Starting M3 SalesTrack migration on live sandbox...")
    for i, legacy_id in enumerate(pending, start=1):
        crm_id = f"ST-{i:05d}"

        for attempt in range(5):
            r = requests.patch(
                f"{BASE}/crm/customers/{legacy_id}",
                headers=H,
                json={
                    "migrated_to_salestrack": "Y",
                    "crm_id": crm_id,
                },
            )

            if r.status_code == 429:
                wait = 2 ** attempt
                print(f"Rate limited on {legacy_id}; waiting {wait}s...")
                time.sleep(wait)
                continue

            r.raise_for_status()
            print(f"{legacy_id} -> {crm_id} [OK]")
            break

        time.sleep(1.1)

    print("M3 complete.")

if __name__ == "__main__":
    main()

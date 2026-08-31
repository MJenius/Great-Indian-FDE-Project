import os
import requests

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")
H = {"Authorization": f"Bearer {KEY}"}

def probe_metadata():
    # Probe root /
    try:
        r = requests.get(BASE + "/", headers=H)
        print(f"=== / === HTTP {r.status_code}")
        print(r.text[:500])
    except Exception as e:
        print(f"=== / === Error: {e}")

    eps = [
        "/checks",
        "/check",
        "/sandbox/checks",
        "/sandbox/status",
        "/score",
        "/scores",
        "/state",
        "/validation",
        "/validate",
        "/tickets/FIX-3415/checks",
        "/tickets/FIX-3415/status",
        "/openapi.json",
        "/docs",
        "/api/docs",
        "/schema"
    ]

    for ep in eps:
        try:
            r = requests.get(BASE + ep, headers=H)
            print(f"\n=== {ep} === HTTP {r.status_code}")
            if r.status_code != 404:
                print(r.text[:500])
        except Exception as e:
            print(f"\n=== {ep} === Error: {e}")

if __name__ == "__main__":
    probe_metadata()

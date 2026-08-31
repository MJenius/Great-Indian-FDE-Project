import os
import json
import requests

BASE = os.environ.get("DRI_BASE", "https://machinehack.com/api/public/sandbox/v1")
KEY = os.environ.get("DRI_KEY", "dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703")
headers = {"Authorization": f"Bearer {KEY}"}

def main():
    r = requests.get(BASE + "/tickets", headers=headers)
    tickets = r.json().get("tickets", [])
    print(f"Total tickets: {len(tickets)}")
    for t in tickets:
        print("=" * 60)
        print(f"[{t.get('ticket_id')}] {t.get('subject')} | {t.get('department')} | Priority: {t.get('priority')}")
        print(t.get("body"))

if __name__ == "__main__":
    main()

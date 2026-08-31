import pandas as pd

cust = pd.read_csv("data/customers.csv")

print("Analysis of raw customer records (Originals 1-40 vs Duplicates 41-80 and 81-85):")
print("=" * 80)
for i in range(40):
    orig = cust.iloc[i]
    dup1 = cust.iloc[i+40]
    extra = ""
    if orig["legacy_id"] in ["C-5014", "C-5019", "C-5020", "C-5024", "C-5029"]:
        extra_dups = cust[cust["customer_name"].str.upper() == orig["customer_name"].upper()]
        extra_dups = extra_dups[extra_dups["legacy_id"] >= "C-5081"]
        if len(extra_dups) > 0:
            extra = f" + Extra: {extra_dups.iloc[0]['legacy_id']} (mig={extra_dups.iloc[0]['migrated_to_salestrack']})"

    print(f"Orig: {orig['legacy_id']} (mig={orig['migrated_to_salestrack']}, crm={orig.get('crm_id')}) <-- Dup: {dup1['legacy_id']} (mig={dup1['migrated_to_salestrack']}, crm={dup1.get('crm_id')}){extra}")

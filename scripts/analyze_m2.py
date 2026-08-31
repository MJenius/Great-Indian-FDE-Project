import pandas as pd

prod = pd.read_csv("data/products.csv")

fts = prod[prod["sku"].str.startswith("FT-")]
dri = prod[~prod["sku"].str.startswith("FT-")]

print("ALL 12 FLOWTECH SKUS & THEIR DATA:")
print("=" * 100)
for _, r in fts.iterrows():
    sku = r["sku"]
    desc = r["description"]
    p19 = r["list_price_2019"]
    p23 = r["list_price_2023"]

    clean_desc = desc
    while clean_desc.endswith(" (FlowTech)"):
        clean_desc = clean_desc[:-len(" (FlowTech)")]

    desc_matches = dri[dri["description"] == clean_desc]

    print(f"[{sku}] Raw: '{desc}'")
    print(f"       Clean Desc: '{clean_desc}' | 2019={p19} | 2023={p23}")
    for _, m in desc_matches.iterrows():
        print(f"       -> Match: {m['sku']} | 2019={m['list_price_2019']} | 2023={m['list_price_2023']}")
    print("-" * 100)

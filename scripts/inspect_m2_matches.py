import requests

BASE = 'https://machinehack.com/api/public/sandbox/v1'
KEY = 'dri_a5b27ce67d5ff93bc8015fb1243d3ed3f6ce93c90f8f8703'
h = {'Authorization': f'Bearer {KEY}'}

def main():
    p = requests.get(BASE + '/erp/products', headers=h).json()['products']
    fts = [x for x in p if x['sku'].startswith('FT-')]
    dri = [x for x in p if not x['sku'].startswith('FT-')]

    print("=" * 95)
    print(f"{'FT SKU':<8} | {'CURRENT MAPPED':<15} | {'TARGET DESC':<40} | {'VALID MATCHES'}")
    print("=" * 95)
    for ft in sorted(fts, key=lambda x: x['sku']):
        target = ft['description']
        while target.endswith(' (FlowTech)'):
            target = target[:-len(' (FlowTech)')]

        matches = [
            x['sku'] for x in dri
            if x['description'] == target
            and x['list_price_2023'] == ft['list_price_2023']
        ]

        mapped = str(ft.get('mapped_dri_sku'))
        print(f"{ft['sku']:<8} | {mapped:<15} | {target:<40} | {matches}")

if __name__ == '__main__':
    main()

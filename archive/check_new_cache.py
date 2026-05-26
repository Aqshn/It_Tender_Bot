import json

with open('grouped_output2.json', encoding='utf-8') as f:
    grouped = json.load(f)

print(f"Mağazalar siyahısı ({len(grouped['magazalar'])} total):")
print("=" * 50)

for store in grouped['magazalar']:
    print(f"• {store['magaza_adi']}: {len(store['mehsullar'])} məhsul")

print("\n" + "=" * 50)
print("Almashop axtarışı:")
almashop_stores = [s for s in grouped['magazalar'] if 'almashop' in s['magaza_adi'].lower()]
print(f"Tapıldı: {len(almashop_stores)} mağaza")

if almashop_stores:
    for store in almashop_stores:
        print(f"  {store['magaza_adi']}: {len(store['mehsullar'])} məhsul")

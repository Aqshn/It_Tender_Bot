import json

# Check what the grouped output actually has
with open('grouped_output2.json', encoding='utf-8') as f:
    grouped = json.load(f)

print("Grouped output sample:")
print("=" * 70)

if grouped.get('magazalar'):
    store = grouped['magazalar'][0]
    print(f"\nMağaza adı: {store['magaza_adi']}")
    
    if store['mehsullar']:
        product = store['mehsullar'][0]
        print(f"\nMəhsulun bütün sahələri:")
        for key in sorted(product.keys()):
            value = product[key]
            if isinstance(value, (list, dict)):
                print(f"  {key}: [...] ({len(value)} items)")
            else:
                val_str = str(value)[:50] if value else "None"
                print(f"  {key}: {val_str}")

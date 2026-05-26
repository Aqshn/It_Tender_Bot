import json

def filter_by_store(data, store_name):
    store_name_lower = store_name.lower()
    result = []
    for item in data:
        if store_name_lower in (item.get("seller_name") or "").lower() or \
           store_name_lower in (item.get("seller_type") or "").lower():
            result.append(item)
    return result

# Read grouped output and extract flat list
with open('grouped_output2.json', encoding='utf-8') as f:
    grouped = json.load(f)
    all_products = []
    for store in grouped['magazalar']:
        all_products.extend(store['mehsullar'])

# Filter by store
filtered = filter_by_store(all_products, "Almashop")
print(f"Found {len(filtered)} products from Almashop store:")
for product in filtered:
    print(f"  - {product['title']} ({product['price']})")

# Save to file
with open('filtered_almashop.json', 'w', encoding='utf-8') as f:
    json.dump(filtered, f, ensure_ascii=False, indent=2)
print("\nSaved to filtered_almashop.json")

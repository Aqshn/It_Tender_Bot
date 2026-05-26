import json

def filter_by_store_and_category(data, store_name, category_name):
    store_name_lower = store_name.lower()
    category_name_lower = category_name.lower()
    result = []
    for item in data:
        if (store_name_lower in (item.get("seller_name") or "").lower() or \
            store_name_lower in (item.get("seller_type") or "").lower()) and \
           category_name_lower in (item.get("category") or "").lower():
            result.append(item)
    return result

# Read grouped output and extract flat list
with open('grouped_output2.json', encoding='utf-8') as f:
    grouped = json.load(f)
    all_products = []
    for store in grouped['magazalar']:
        all_products.extend(store['mehsullar'])

# Show available categories for Almashop
print("Almashop products by category:")
almashop = [p for p in all_products if p.get("seller_name") == "Almashop"]
categories = {}
for product in almashop:
    cat = product.get("category", "Bilinməmiş")
    if cat not in categories:
        categories[cat] = []
    categories[cat].append(product)

for cat, products in categories.items():
    print(f"  {cat}: {len(products)} products")
    for p in products:
        print(f"    - {p['title']} ({p['price']})")

# Test category filter
print("\n\nFilter test - Almashop + Elektronika:")
filtered = filter_by_store_and_category(all_products, "Almashop", "Elektronika")
print(f"Found {len(filtered)} products")
for product in filtered:
    print(f"  - {product['title']} (Category: {product['category']}, Price: {product['price']})")

# Save to file
with open('filtered_almashop_elektronika.json', 'w', encoding='utf-8') as f:
    json.dump(filtered, f, ensure_ascii=False, indent=2)
print("\nSaved to filtered_almashop_elektronika.json")

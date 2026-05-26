import json

with open('simple_almashop.json', encoding='utf-8') as f:
    data = json.load(f)
    
print(f"Məhsul sayı: {len(data)}")
print("\nMəhsullar:")
for i, product in enumerate(data[:10], 1):
    print(f"  {i}. {product.get('title', 'Başlıq yoxdur')}")
    print(f"     Mağaza: {product.get('seller_name', 'Bilinməmiş')}")
    print(f"     Qiymət: {product.get('price', 'Qiymət yoxdur')}")
    print(f"     Kateqoriya: {product.get('category', 'Bilinməmiş')}")
    print()

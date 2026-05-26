#!/usr/bin/env python3
"""
FILTRLƏMƏ VƏ QRUPLAŞDIRMA - MİSAL FAYLLAR
==========================================

Bu skript parçer ilə filtrləmə istifadəsinin praktik nümunələrini göstərir.
"""

import json

print("=" * 70)
print("PARCER FILTRLƏMƏ VƏ QRUPLAŞDIRMA - NÜMUNƏLƏR")
print("=" * 70)

# 1. Mağaza adı ilə filtrləmə
print("\n1. MAĞAZA ADINA GÖRƏ FİLTRLƏMƏ")
print("-" * 70)
print("Komanda:")
print('  py parcer/parcer.py --url "https://tap.az/elanlar" --pages 5 \\')
print('    --filter-store "Almashop" --output almashop_products.json')
print()

with open('filtered_almashop.json', encoding='utf-8') as f:
    almashop = json.load(f)
    print(f"Nəticə: {len(almashop)} məhsul tapıldı\n")
    for i, product in enumerate(almashop, 1):
        print(f"  {i}. {product['title']}")
        print(f"     Qiymət: {product['price']}")
        print(f"     Kateqoriya: {product['category']}")
        print()

# 2. Mağaza + Kateqoriya filtrləməsi
print("\n2. MAĞAZA + KATEQORİYA İLƏ FİLTRLƏMƏ")
print("-" * 70)
print("Komanda:")
print('  py parcer/parcer.py --url "https://tap.az/elanlar" --pages 5 \\')
print('    --filter-store "Almashop" --filter-category "Elektronika" \\')
print('    --output almashop_electronics.json')
print()

with open('filtered_almashop_elektronika.json', encoding='utf-8') as f:
    almashop_electronics = json.load(f)
    print(f"Nəticə: {len(almashop_electronics)} məhsul tapıldı\n")
    for i, product in enumerate(almashop_electronics, 1):
        print(f"  {i}. {product['title']}")
        print(f"     Qiymət: {product['price']}")
        print()

# 3. Qruplaşdırma
print("\n3. MAĞAZALARA GÖRƏ QRUPLAŞDIRMA")
print("-" * 70)
print("Komanda:")
print('  py parcer/parcer.py --url "https://tap.az/elanlar" --pages 5 \\')
print('    --group-by-store --output grouped_output.json')
print()

with open('grouped_output2.json', encoding='utf-8') as f:
    grouped = json.load(f)
    print(f"Nəticə: {len(grouped['magazalar'])} mağaza qruplaşdırıldı\n")
    
    total_products = 0
    for store in grouped['magazalar']:
        products_count = len(store['mehsullar'])
        total_products += products_count
        print(f"  • {store['magaza_adi']}: {products_count} məhsul")
    
    print(f"\nCəmi: {total_products} məhsul, {len(grouped['magazalar'])} mağazadır")

print("\n" + "=" * 70)
print("DİQQƏT: Filtrləmə hərflərə diqqət sız (case-insensitive) işləyir!")
print("        Qismən uyğunluq da qəbul olunur (məs: 'Alma' -> 'Almashop')")
print("=" * 70)

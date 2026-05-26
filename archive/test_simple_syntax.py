import json

# Test with the existing grouped data
with open('grouped_output2.json', encoding='utf-8') as f:
    grouped = json.load(f)
    
    # Extract flat list
    all_products = []
    for store in grouped['magazalar']:
        all_products.extend(store['mehsullar'])
    
    print("=" * 70)
    print("SADƏ SİNTAKS - TEST")
    print("=" * 70)
    
    # Test 1: Just store
    print("\n1. SADƏCƏ MAĞAZA ADINA GÖRƏ AXTARIŞ")
    print("   Komanda: py parcer/parcer.py --store \"Almashop\" --output result.json")
    almashop = [p for p in all_products if 'almashop' in p.get('seller_name', '').lower()]
    print(f"   Nəticə: {len(almashop)} məhsul")
    
    # Test 2: Store + Category
    print("\n2. MAĞAZA + KATEQORİYA İLƏ AXTARIŞ")
    print("   Komanda: py parcer/parcer.py --store \"Almashop\" --cat \"Elektronika\" --output result.json")
    almashop_electronics = [p for p in almashop if 'elektronika' in p.get('category', '').lower()]
    print(f"   Nəticə: {len(almashop_electronics)} məhsul")
    
    if almashop_electronics:
        print("\n   Məhsullar:")
        for p in almashop_electronics[:5]:
            print(f"     - {p['title']}")
    
    print("\n" + "=" * 70)
    print("İSTİFADƏ NÜMUNƏLƏRİ:")
    print("=" * 70)
    print("\n# Almashop mağazasının bütün məhsulları")
    print("py parcer/parcer.py --store \"Almashop\" --output almashop_all.json")
    
    print("\n# Almashop mağazasının Elektronika məhsulları")
    print("py parcer/parcer.py --store \"Almashop\" --cat \"Elektronika\" --output almashop_electronics.json")
    
    print("\n# Bütün mağazalar (qruplaşdırılmış)")
    print("py parcer/parcer.py --group-by-store --output all_stores.json")
    
    print("\n# Almashop mağazasının Ev məhsulları")
    print("py parcer/parcer.py --store \"Almashop\" --cat \"Ev\" --output almashop_home.json")
    
    print("\n" + "=" * 70)

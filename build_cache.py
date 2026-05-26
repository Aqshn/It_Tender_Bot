"""
Cache yaradıcı - ilk dəfə tap.az-dan 10 səhifə çəkir və mağazalara görə qrupla
"""
import sys
import json
from pathlib import Path
from urllib.parse import urljoin

# Add parcer to path
sys.path.insert(0, str(Path(__file__).parent))

from parcer.parcer import (
    create_session, scrape_category, scrape_detail, 
    group_by_store, to_json, BASE_URL
)

def build_cache():
    """Build grouped_output2.json cache from scratch"""
    session = create_session()
    
    print("📥 10 səhifə çəkilir... (Bu biraz vaxt alacaq)")
    
    # Scrape 10 pages
    url = urljoin(BASE_URL, "/elanlar")
    items = scrape_category(session, url, pages=10, store_only=False)
    
    print(f"✓ {len(items)} elan tapıldı")
    print("📋 Detallar çəkilir...")
    
    # Get details
    detailed = []
    for i, item in enumerate(items, 1):
        try:
            d = scrape_detail(session, item.url)
            detailed.append({
                'url': d.url,
                'title': d.title,
                'price': d.price,
                'seller_name': d.seller_name or 'Naməlum',
                'category': d.category,
                'location': d.location,
                'description': d.description,
            })
        except Exception as e:
            print(f"  ⚠ Elan #{i} skip edildi: {e}")
        
        if i % 10 == 0:
            print(f"  {i}/{len(items)}...")
    
    print(f"✓ {len(detailed)} məhsulun detalları alındı")
    
    # Group by store
    grouped_data = group_by_store(detailed)
    
    # Save
    with open("grouped_output2.json", 'w', encoding='utf-8') as f:
        f.write(to_json(grouped_data))
    
    print(f"\n✅ Cache yaradıldı: grouped_output2.json")
    print(f"📊 Mağazalar: {len(grouped_data['magazalar'])}")
    
    # List stores
    for store in sorted(grouped_data['magazalar'], key=lambda x: len(x['mehsullar']), reverse=True)[:15]:
        print(f"  • {store['magaza_adi']}: {len(store['mehsullar'])} məhsul")

if __name__ == "__main__":
    build_cache()

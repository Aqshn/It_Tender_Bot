import json
import sys
sys.path.insert(0, 'parcer')

from parcer import create_session, scrape_category, scrape_detail, asdict
from urllib.parse import urljoin

BASE_URL = "https://tap.az"

session = create_session()
url = urljoin(BASE_URL, "/elanlar")

print("Səhifə toplanır...")
items = scrape_category(session, url, pages=1, store_only=False)
print(f"Tapıldı: {len(items)} elan\n")

if items:
    print("İlk 2 elan - Detaylı məlumat toplanır:\n")
    for i, item in enumerate(items[:2], 1):
        print(f"{i}. {item.title}")
        
        # Try to fetch detail
        try:
            detail = scrape_detail(session, item.url)
            detail_dict = asdict(detail)
            print(f"   ✓ seller_name: {detail_dict.get('seller_name', 'None')}")
            print(f"   ✓ seller_type: {detail_dict.get('seller_type', 'None')}")
            print(f"   ✓ category: {detail_dict.get('category', 'None')}")
        except Exception as e:
            print(f"   ✗ Xəta: {str(e)[:60]}")
        print()


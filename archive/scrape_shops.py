"""
Tap.az/shops sehifesinden magaza katalogunu cek
- Magaza adi
- Nomu
- Kategoriyalari
- Elan sayisi
"""
import sys
import json
import time
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "https://tap.az"

def get_stores_catalog():
    """Tap.az/shops'dan magaza katalogu cek"""
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "az-AZ,az;q=0.9,en;q=0.8",
    }
    
    stores = []
    page = 1
    
    while True:
        url = f"https://tap.az/shops?page={page}"
        print(f"📥 Sehife {page}: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
        except Exception as e:
            print(f"  ❌ Xeta: {e}")
            break
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Store cards'lari axtarır
        store_cards = soup.find_all(['div'], class_=lambda x: x and ('card' in x.lower() or 'shop' in x.lower() or 'store' in x.lower()))
        
        if not store_cards:
            # Alternativ axtarış
            store_cards = soup.find_all(['div', 'article'], recursive=True)
        
        if not store_cards:
            print(f"  ✓ Hec bir magaza tapilmadi - bitdi")
            break
        
        new_stores = 0
        
        for card in store_cards:
            try:
                # Store name ve link
                store_link = card.find('a', href=True)
                if not store_link or '/shop/' not in store_link.get('href', ''):
                    continue
                
                store_name = store_link.get_text(strip=True)
                store_url = store_link.get('href', '')
                
                if not store_name or len(store_name) < 2:
                    continue
                
                # Elan sayisi (meselen "321 elan")
                elan_text = card.get_text()
                elan_count = None
                
                # Numru (telefo) - "Show number" dugmesi var mi?
                phone_button = card.find('button', string=lambda s: s and 'Nomre' in s if s else False)
                has_phone = phone_button is not None
                
                store_data = {
                    'name': store_name,
                    'url': urljoin(BASE_URL, store_url) if not store_url.startswith('http') else store_url,
                    'has_phone': has_phone,
                    'listings_text': elan_text[:200]  # Ilk 200 simvol
                }
                
                stores.append(store_data)
                new_stores += 1
                
            except Exception as e:
                continue
        
        print(f"  ✓ {new_stores} magaza tapildi")
        
        if new_stores == 0:
            break
        
        page += 1
        time.sleep(1)  # Rate limiting
    
    return stores

def scrape_stores_from_shops():
    """Magaza sehifesini JavaScript ile parse et"""
    print("🔄 Tap.az/shops sehifesinden magaza katalogu cekiliyor...\n")
    
    stores = get_stores_catalog()
    
    print(f"\n✅ Cekme tamamlandi: {len(stores)} magaza\n")
    
    if stores:
        print("📋 MAGAZALAR:\n")
        for i, store in enumerate(stores[:20], 1):
            print(f"{i}. {store['name']}")
            print(f"   URL: {store['url']}")
            print(f"   Telefon: {'✓ Var' if store['has_phone'] else '✗ Yok'}")
            print()
        
        if len(stores) > 20:
            print(f"\n... ve {len(stores) - 20} daha\n")
        
        # JSON sehifesine yaz
        with open("tap_stores_catalog.json", 'w', encoding='utf-8') as f:
            json.dump({
                'total': len(stores),
                'stores': stores
            }, f, ensure_ascii=False, indent=2)
        
        print(f"✅ tap_stores_catalog.json sehifesine kaydedildi")
    else:
        print("⚠ Hec bir magaza tapilmadi")

if __name__ == "__main__":
    scrape_stores_from_shops()

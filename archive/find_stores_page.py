"""
Tap.az mağaza kataloqusu çəkmə
Mağaza adı, nömrəsi, kateqoriyaları
"""
import sys
import json
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://tap.az"

def get_stores_page():
    """Tap.az mağazalar səhifəsini aç"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    
    # Mağazalar üçün mümkün URLlar
    possible_urls = [
        "https://tap.az/shops",  
        "https://tap.az/magaza",
        "https://tap.az/magazines",
        "https://tap.az/stores",
    ]
    
    session = requests.Session()
    session.headers.update(headers)
    
    for url in possible_urls:
        try:
            print(f"🔍 Cəhd: {url}")
            response = session.get(url, timeout=10)
            if response.status_code == 200:
                print(f"✓ Tapıldı!")
                return response.text
        except Exception as e:
            print(f"  ✗ Olmadı: {e}")
    
    # Ümumi elanlar səhifəsindən mağazaları çıxar
    print(f"\n📥 Ümumi elanlardan mağaza siyahısı çəkilir...")
    try:
        response = session.get("https://tap.az/elanlar", timeout=10)
        return response.text
    except:
        return None

def extract_stores_from_html(html):
    """HTML-dən mağazaları çıxar"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Mümkün selector-lar
    print("🔎 Mağaza məlumatları axtarılır...")
    
    stores = {}
    
    # 1. Shop cards axtarır
    shop_cards = soup.find_all(['div', 'a'], class_=lambda x: x and ('shop' in x.lower() or 'store' in x.lower()))
    print(f"  Shop card: {len(shop_cards)} tapıldı")
    
    # 2. Link etiketlərində mağaza adlarını axtarır
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
        if '/shop/' in href or '/store/' in href or '/shops/' in href:
            if text and len(text) > 2:
                stores[text] = href
    
    print(f"  Linkdən: {len(stores)} mağaza tapıldı")
    
    return stores

if __name__ == "__main__":
    html = get_stores_page()
    
    if html:
        stores = extract_stores_from_html(html)
        
        print(f"\n📋 Cəmi: {len(stores)} mağaza")
        print("\nMağazalar:")
        for name, url in sorted(stores.items())[:20]:
            print(f"  • {name}")
            print(f"    {url}\n")
        
        # Siyahını saxla
        with open("tap_stores.json", 'w', encoding='utf-8') as f:
            json.dump(list(stores.keys()), f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ tap_stores.json-ə saxlanıldı")
    else:
        print("❌ Veri çəkilə bilmədi")

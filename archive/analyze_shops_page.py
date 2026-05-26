"""
Tap.az /shops sehifesinin strukturunu analiz et
"""
import sys
import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

response = requests.get("https://tap.az/shops", headers=headers, timeout=10)
soup = BeautifulSoup(response.text, 'html.parser')

print("=== TAP.AZ SHOPS SAHIFESI ===")

print("=== TAP.AZ SHOPS SAHIFESI ===\n")

# Başlıq
title = soup.find('title')
print(f"Title: {title.text if title else 'N/A'}\n")

# HTML uzunluğu
print(f"HTML length: {len(response.text)} characters\n")

# Ilk text
print("First 1500 chars of HTML:")
print(response.text[:1500])
print("\n" + "="*50)

# Divleri axtarır
divs = soup.find_all('div', limit=10)
print(f"\nFirst 10 divs:")
for i, div in enumerate(divs):
    class_attr = div.get('class', [])
    id_attr = div.get('id', '')
    text = div.get_text(strip=True)[:30]
    print(f"{i+1}. class={class_attr} id={id_attr} text={text}")

# Linkleri axtarır
links = soup.find_all('a', limit=20)
print(f"\nFirst 20 links:")
for link in links:
    href = link.get('href', '')
    text = link.get_text(strip=True)
    if text:
        print(f"  {text[:40]} -> {href[:50]}")

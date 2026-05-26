import json
import re
from pathlib import Path
from urllib.parse import urljoin
from time import sleep
from playwright.sync_api import sync_playwright
from openpyxl import Workbook

BASE_URL = 'https://lalafo.az'
workspace = Path(r'c:\Users\user\Desktop\Vs code projects\Parcer')
input_names = ['all_lalafo_fixed.json','all_lalafo.json']
for name in input_names:
    p = workspace / name
    if p.exists():
        input_path = p
        break
else:
    raise SystemExit('No all_lalafo input found')

data = json.loads(input_path.read_text(encoding='utf-8'))
sellers = data.get('sellers', [])

# helper

def normalize_url(href: str) -> str:
    if not href:
        return ''
    return urljoin(BASE_URL, href)


def scroll_to_bottom(page):
    last_height = page.evaluate('() => document.body.scrollHeight')
    stable = 0
    attempts = 0
    while attempts < 30:
        page.evaluate('() => window.scrollTo(0, document.body.scrollHeight)')
        page.wait_for_timeout(800)
        new_h = page.evaluate('() => document.body.scrollHeight')
        attempts += 1
        if new_h == last_height:
            stable += 1
        else:
            stable = 0
            last_height = new_h
        if stable >= 3:
            break


mismatches = []
updated = 0

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width':1200,'height':900})
    page = context.new_page()

    for idx, seller in enumerate(sellers, 1):
        shop_url = (seller.get('shop_url') or '').strip()
        seller_id = str(seller.get('seller_id') or '').strip()
        if shop_url and shop_url.startswith('http'):
            url = shop_url
        elif seller_id and seller_id.isdigit():
            url = f'{BASE_URL}/user/{seller_id}'
        elif shop_url:
            url = normalize_url(shop_url)
        else:
            # fallback to profile by seller_id
            url = f'{BASE_URL}/user/{seller_id}' if seller_id else ''

        if not url:
            print(f'[{idx}/{len(sellers)}] Skipping empty URL for seller {seller.get("shop_name","")}')
            continue

        try:
            print(f'[{idx}/{len(sellers)}] Visiting {url}')
            resp = page.goto(url, timeout=30000)
            if resp and resp.status == 404:
                print('  -> 404')
                continue
            page.wait_for_timeout(1000)
            scroll_to_bottom(page)
            # collect unique ad hrefs
            ad_links = set()
            for a in page.query_selector_all("a[href*='/ads/']"):
                try:
                    href = (a.get_attribute('href') or '').strip()
                    if not href:
                        continue
                    full = normalize_url(href)
                    # filter out anchors that are not ad links
                    if '/ads/' in full:
                        ad_links.add(full.split('#')[0])
                except Exception:
                    continue

            counted = len(ad_links)
            if counted != int(seller.get('ads_count', 0) or 0):
                mismatches.append({'index': idx, 'shop_name': seller.get('shop_name',''), 'url': url, 'merged': seller.get('ads_count'), 'counted': counted})
                seller['ads_count'] = counted
                updated += 1
                print(f'  -> MISMATCH: merged={mismatches[-1]["merged"]} counted={counted} (updated)')
            else:
                print(f'  -> OK ({counted})')

            # small delay to be polite
            page.wait_for_timeout(400)
        except Exception as e:
            print(f'  -> ERROR visiting {url}: {e}')
            continue

    # write outputs
    out_path = workspace / 'all_lalafo_checked.json'
    data['sellers'] = sellers
    data['total_pro_sellers'] = len(sellers)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding='utf-8')

    wb = Workbook()
    ws = wb.active
    ws.append(['seller_id','shop_name','shop_url','ads_count','mobile_numbers','categories'])
    for s in sellers:
        ws.append([s.get('seller_id',''), s.get('shop_name',''), s.get('shop_url',''), s.get('ads_count',0), ';'.join(s.get('mobile_numbers',[])), ';'.join(s.get('categories',[]))])
    wb.save(workspace / 'all_lalafo_checked.xlsx')

    browser.close()

print(f'Done. checked={len(sellers)} mismatches={len(mismatches)} updated={updated}')
for m in mismatches[:30]:
    print(m)

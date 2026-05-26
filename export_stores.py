"""
Tap.az/shops səhifəsindən bütün mağazaları çəkir,
telefon nömrələri və əsas kateqoriya ilə birlikdə JSON/CSV çıxış yaradır.
"""
from __future__ import annotations

import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "https://tap.az"
GRAPHQL_URL = f"{BASE_URL}/graphql"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "az-AZ,az;q=0.9,en;q=0.8",
}

GET_SHOPS_QUERY = """
query GetShops($after: String, $before: String, $first: Int, $last: Int, $order: ShopOrderEnum, $search: String, $seed: Int, $categoriesIds: [ID!]) {
  shops(
    after: $after
    before: $before
    first: $first
    last: $last
    order: $order
    search: $search
    seed: $seed
    categoriesIds: $categoriesIds
  ) {
    nodes {
      id
      name
      adsCount
      timeOnPlatform
      uri
      categories {
        id
        name
        slug
        path
        count
      }
    }
    pageInfo {
      endCursor
      hasNextPage
    }
    totalCount
  }
}
"""


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    return session


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        value = value.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def fetch_all_shops(session: requests.Session) -> list[dict[str, Any]]:
    shops: list[dict[str, Any]] = []
    after: str | None = None
    page = 1

    while True:
        payload = {
            "operationName": "GetShops",
            "variables": {
                "after": after,
                "before": None,
                "first": 50,
                "last": None,
                "order": "DEFAULT",
                "search": None,
                "seed": 20,
                "categoriesIds": None,
            },
            "query": GET_SHOPS_QUERY,
        }

        response = session.post(GRAPHQL_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        shops_block = data.get("data", {}).get("shops") or {}
        nodes = shops_block.get("nodes") or []
        page_info = shops_block.get("pageInfo") or {}

        if not nodes:
            break

        shops.extend(nodes)
        print(f"  Səhifə {page}: {len(nodes)} mağaza")

        if not page_info.get("hasNextPage"):
            break

        after = page_info.get("endCursor")
        if not after:
            break

        page += 1

    return shops


def fetch_store_details(store_url: str) -> dict[str, list[str] | str | None]:
    response = requests.get(store_url, headers=DEFAULT_HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        return {"mobile_numbers": [], "category": None}

    data = json.loads(script.string)
    shop = data.get("props", {}).get("pageProps", {}).get("shopDetails", {})

    phones = unique([phone for phone in (shop.get("phones") or []) if isinstance(phone, str)])
    categories = shop.get("categories") or []

    category = categories[0].get("name") if categories and isinstance(categories[0], dict) else None

    return {"mobile_numbers": phones, "category": category}


def build_cache() -> None:
    session = create_session()

    print("📥 Bütün mağazalar yığılır...")
    raw_shops = fetch_all_shops(session)
    print(f"✅ Cəmi mağaza tapıldı: {len(raw_shops)}")
    print("📋 Detallar çəkilir...")

    enriched_stores: list[dict[str, Any]] = []
    store_jobs: list[tuple[int, dict[str, Any], str]] = []
    for index, shop in enumerate(raw_shops, 1):
        store_url = shop.get("uri") or ""
        if store_url and not store_url.startswith("http"):
            store_url = f"{BASE_URL}{store_url}"

        store_jobs.append((index, shop, store_url))

    def enrich_shop(job: tuple[int, dict[str, Any], str]) -> dict[str, Any]:
        index, shop, store_url = job
        print(f"  {index}/{len(raw_shops)}: {shop.get('name', 'Naməlum')}")
        try:
            details = fetch_store_details(store_url)
        except Exception as exc:
            print(f"    ⚠ məlumat alınmadı: {exc}")
            details = {"mobile_numbers": [], "category": None}

        categories = shop.get("categories") or []
        category = details["category"]
        if not category and categories and isinstance(categories[0], dict):
            category = categories[0].get("name")

        mobile_numbers = details["mobile_numbers"] or []

        return {
            "name": shop.get("name"),
            "url": store_url,
            "time_on_platform": shop.get("timeOnPlatform"),
            "ads_count": shop.get("adsCount"),
            "mobile_numbers": mobile_numbers,
            "category": category,
        }

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(enrich_shop, job) for job in store_jobs]
        for future in as_completed(futures):
            enriched_stores.append(future.result())

    enriched_stores.sort(key=lambda item: (item.get("name") or "").lower())

    output = {
        "total_stores": len(enriched_stores),
        "source": "https://tap.az/shops",
        "stores": enriched_stores,
    }

    with open("tap_all_stores.json", "w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)

    with open("tap_all_stores.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Magaza Adi", "URL", "Elan Sayisi", "Platform Suresi", "Mobil Nomreler", "Kateqoriya"])
        for store in enriched_stores:
            writer.writerow(
                [
                    store["name"] or "",
                    store["url"] or "",
                    store["ads_count"] or "",
                    store["time_on_platform"] or "",
                    ", ".join(store["mobile_numbers"]) if store["mobile_numbers"] else "",
                    store["category"] or "",
                ]
            )

    print("✅ Veri saxlandi:")
    print(f"📄 tap_all_stores.json ({len(enriched_stores)} magaza)")
    print(f"📊 tap_all_stores.csv ({len(enriched_stores)} magaza)")

    print("\n" + "=" * 60)
    print("MAGAZALAR SİYAHISI:")
    print("=" * 60 + "\n")
    for i, store in enumerate(enriched_stores, 1):
        phones_text = ", ".join(store["mobile_numbers"]) if store["mobile_numbers"] else "Bilinmir"
        print(
            f"{i:3}. {store['name']:<30} | "
            f"Telefon: {phones_text} | "
            f"Kateqoriya: {store['category'] or 'Bilinmir'}"
        )

    print("\n" + "=" * 60)
    print(f"Cemi: {len(enriched_stores)} magaza")
    print("=" * 60)


if __name__ == "__main__":
    build_cache()
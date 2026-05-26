"""Scrape Turbo.az avtosalonlar and export name, url, ads count, and phone numbers.

The listing page already contains all dealer cards plus a hidden phone source for each card,
so the parser can stay fully HTML-based and does not need to click into every dealer page.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from playwright.sync_api import sync_playwright


BASE_URL = "https://turbo.az"
LISTING_URL = f"{BASE_URL}/avtosalonlar"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "az-AZ,az;q=0.9,en;q=0.8",
}


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


def normalize_phone(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""

    value = re.sub(r"^tel:", "", value, flags=re.IGNORECASE)
    value = re.sub(r"[\s\-()]+", "", value)

    if value.startswith("+"):
        digits = "+" + re.sub(r"\D", "", value)
        return digits

    digits = re.sub(r"\D", "", value)
    if digits.startswith("994") and len(digits) >= 12:
        return "+" + digits
    if digits.startswith("0") and len(digits) == 10:
        return "+994" + digits[1:]
    if len(digits) == 9:
        return "+994" + digits

    return value


def parse_listing_page(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select('a.shops-i[href^="/avtosalonlar/"]')

    items: list[dict[str, Any]] = []
    for card in cards:
        href = (card.get("href") or "").strip()
        if not href or href == "/avtosalonlar":
            continue

        name_node = card.select_one(".js-shops-title")
        ads_node = card.select_one(".shops-i__ads-count")

        name = name_node.get_text(" ", strip=True) if name_node else card.get("aria-label", "").strip()
        ads_count_text = ads_node.get_text(" ", strip=True) if ads_node else "0"
        ads_count_match = re.search(r"\d+", ads_count_text)
        ads_count = int(ads_count_match.group(0)) if ads_count_match else 0

        items.append({
            "name": name,
            "url": urljoin(BASE_URL, href),
            "ads_count": ads_count,
            "mobile_numbers": [],
        })

    return items


def extract_phone_values_from_detail(page: Any) -> list[str]:
    phone_values: list[str] = []

    try:
        button = page.locator('.product-phones__btn-value, .js-shop-card-phone-btn, .js-shop-phone-btn').first
        if button.count() > 0:
            try:
                button.click(timeout=5000)
                page.wait_for_timeout(800)
            except Exception:
                pass
    except Exception:
        pass

    phone_selectors = [
        ".product-phones a[href^='tel:']",
        ".shop--header-right a[href^='tel:']",
    ]

    for selector in phone_selectors:
        try:
            anchors = page.locator(selector).all()
            if not anchors:
                continue
            for anchor in anchors:
                href = anchor.get_attribute("href") or ""
                text = anchor.inner_text().strip()
                phone_values.extend([href, text])
            if phone_values:
                break
        except Exception:
            continue

    return unique([
        normalize_phone(value)
        for value in phone_values
        if normalize_phone(value)
    ])


def enrich_with_phones(items: list[dict[str, Any]]) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 900})
        page = context.new_page()

        for index, item in enumerate(items, 1):
            try:
                page.goto(item["url"], timeout=60000)
                page.wait_for_timeout(800)
                item["mobile_numbers"] = extract_phone_values_from_detail(page)
                print(f"  {index}/{len(items)}: {item.get('name', '')} -> {len(item['mobile_numbers'])} phones")
            except Exception as exc:
                print(f"  {index}/{len(items)}: {item.get('name', '')} -> phone fetch failed: {exc}")
                item["mobile_numbers"] = []

        browser.close()


def export_json(items: list[dict[str, Any]], output_path: Path) -> None:
    payload = {
        "source": LISTING_URL,
        "total_saloons": len(items),
        "saloons": items,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def export_csv(items: list[dict[str, Any]], output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["name", "url", "ads_count", "mobile_numbers"])
        for item in items:
            writer.writerow([
                item.get("name", ""),
                item.get("url", ""),
                item.get("ads_count", 0),
                "; ".join(item.get("mobile_numbers", [])),
            ])


def export_xlsx(items: list[dict[str, Any]], output_path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Turbo Avtosalonlar"

    headers = ["name", "url", "ads_count", "mobile_numbers"]
    worksheet.append(headers)

    for item in items:
        worksheet.append([
            item.get("name", ""),
            item.get("url", ""),
            item.get("ads_count", 0),
            "; ".join(item.get("mobile_numbers", [])),
        ])

    for cell in worksheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(wrapText=True, vertical="center")

    worksheet.freeze_panes = "A2"

    for column_cells in worksheet.columns:
        letter = column_cells[0].column_letter
        max_length = 0
        for cell in column_cells:
            cell_value = "" if cell.value is None else str(cell.value)
            max_length = max(max_length, len(cell_value))
        worksheet.column_dimensions[letter].width = min(max(12, int(max_length * 1.15)), 80)

    workbook.save(output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export Turbo.az avtosalonlar to JSON, CSV and XLSX")
    parser.add_argument("--output-dir", default=".", help="Directory for output files")
    parser.add_argument("--prefix", default="turbo_avtosalonlar", help="Output filename prefix")
    parser.add_argument("--json", dest="write_json", action="store_true", default=True, help="Write JSON output")
    parser.add_argument("--no-json", dest="write_json", action="store_false", help="Disable JSON output")
    parser.add_argument("--csv", dest="write_csv", action="store_true", default=True, help="Write CSV output")
    parser.add_argument("--no-csv", dest="write_csv", action="store_false", help="Disable CSV output")
    parser.add_argument("--xlsx", dest="write_xlsx", action="store_true", default=True, help="Write XLSX output")
    parser.add_argument("--no-xlsx", dest="write_xlsx", action="store_false", help="Disable XLSX output")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    session = create_session()
    response = session.get(LISTING_URL, timeout=30)
    response.raise_for_status()

    items = parse_listing_page(response.text)
    enrich_with_phones(items)

    print(f"Found {len(items)} avtosalonlar")

    if args.write_json:
        json_path = output_dir / f"{args.prefix}.json"
        export_json(items, json_path)
        print(f"Wrote {json_path}")

    if args.write_csv:
        csv_path = output_dir / f"{args.prefix}.csv"
        export_csv(items, csv_path)
        print(f"Wrote {csv_path}")

    if args.write_xlsx:
        xlsx_path = output_dir / f"{args.prefix}.xlsx"
        export_xlsx(items, xlsx_path)
        print(f"Wrote {xlsx_path}")


if __name__ == "__main__":
    main()
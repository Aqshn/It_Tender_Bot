"""Lalafo PRO satıcıları kateqoriyalar üzrə çıxarır, email və kateqoriya ilə saxlayır.

Playwright-based rewrite (synchronous API).
"""
import json
import re
from typing import Any
import argparse
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, Page
from openpyxl import Workbook


BASE_URL = "https://lalafo.az"
OUTPUT_FILE = "lalafo_pro_shops.json"
MAX_SCROLL_ATTEMPTS = 12
SCROLL_STABLE_ITERATIONS = 3
MAX_PAGES_PER_CATEGORY = 5
CONSECUTIVE_EMPTY_PAGES_TO_STOP = 2
DELAY_BETWEEN_ADS = 1
DELAY_BETWEEN_CATEGORIES = 2


def normalize_url(value: str | None) -> str:
    if not value:
        return ""
    return urljoin(BASE_URL, value)


def unique_texts(values: list[str]) -> list[str]:
    return list(dict.fromkeys([value.strip() for value in values if value and value.strip()]))


AZ_TRANSLIT = str.maketrans({
    "ə": "e",
    "Ə": "E",
    "ı": "i",
    "I": "I",
    "İ": "I",
    "ş": "s",
    "Ş": "S",
    "ç": "c",
    "Ç": "C",
    "ö": "o",
    "Ö": "O",
    "ü": "u",
    "Ü": "U",
    "ğ": "g",
    "Ğ": "G",
    "ñ": "n",
    "Ñ": "N",
    "-": "_",
    "/": "_",
})


def slugify_filename(text: str) -> str:
    cleaned = (text or "").translate(AZ_TRANSLIT)
    cleaned = re.sub(r"[^0-9A-Za-z]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_").lower()
    return cleaned or "category"


def export_xlsx(rows: list[dict[str, Any]], file_path: str) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Lalafo"

    headers = ["seller_id", "shop_name", "shop_url", "mobile_numbers", "categories", "ads_count"]
    worksheet.append(headers)

    for row in rows:
        worksheet.append([
            row.get("seller_id", ""),
            row.get("shop_name", ""),
            row.get("shop_url", ""),
            ";".join(row.get("mobile_numbers", [])),
            ";".join(row.get("categories", [])),
            row.get("ads_count", 0),
        ])

    workbook.save(file_path)


def normalize_shop_name(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip().lower()


def normalize_for_compare(value: str | None) -> str:
    return re.sub(r"[^a-z0-9а-яա-ֆəğıöşüç0-9]+", "", normalize_shop_name(value))


def canonical_seller_key(seller_id: str | None, shop_url: str | None, shop_name: str | None = None) -> str:
    candidate_values = [shop_url or "", seller_id or ""]
    for candidate in candidate_values:
        match = re.search(r"/user/(\d+)", candidate)
        if match:
            return match.group(1)

    if seller_id and seller_id.isdigit():
        return seller_id

    if shop_url:
        return shop_url.strip()

    return normalize_shop_name(shop_name) or (seller_id or "").strip()


def focus_browser(page: Page) -> None:
    try:
        page.bring_to_front()
    except Exception:
        pass
    try:
        page.evaluate("() => window.focus()")
    except Exception:
        pass


def scroll_to_bottom(page: Page) -> None:
    last_height = page.evaluate("() => document.body.scrollHeight")
    stable_count = 0
    attempts = 0

    while attempts < MAX_SCROLL_ATTEMPTS:
        page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(700)
        new_height = page.evaluate("() => document.body.scrollHeight")
        attempts += 1

        if new_height == last_height:
            stable_count += 1
        else:
            stable_count = 0
            last_height = new_height

        if stable_count >= SCROLL_STABLE_ITERATIONS:
            break


def get_categories(page: Page) -> dict[str, str]:
    categories: dict[str, str] = {}
    try:
        # Only look inside the main category grid for top-level categories
        category_selectors = [
            ".CategoryGrid_categoryGridContainer__rhErq a",
        ]
        # Collect raw hrefs for debugging
        raw_hrefs: list[tuple[str, str, str]] = []  # (selector, href, text)

        for selector in category_selectors:
            try:
                for el in page.query_selector_all(selector):
                    try:
                        href = el.get_attribute("href") or ""
                        text = (el.inner_text() or "").strip()
                        raw_hrefs.append((selector, href, text))
                        if href and text:
                            # Restrict to top-level category paths used on homepage (e.g., /azerbaijan/elektronika)
                            if href.startswith("/azerbaijan/"):
                                if text.lower() not in {"bütün elanlar", "hamı", "all", "вse", "", "lalafoda yeni"}:
                                    cat_url = normalize_url(href)
                                    if cat_url not in categories.values():
                                        categories[text] = cat_url
                    except Exception:
                        continue
            except Exception:
                continue

        # Write discovered raw hrefs to a file for inspection
        try:
            with open("discovered_categories.txt", "w", encoding="utf-8") as fh:
                for sel, href, text in raw_hrefs:
                    fh.write(f"{sel}\t{href}\t{text}\n")
        except Exception:
            pass

        # If no categories found via selectors, do not fall back to legacy '/c/' paths.
        # Returning empty `categories` is preferable so the caller can decide how to proceed.

    except Exception as e:
        print(f"⚠ Kateqoriya oxunması xətası: {e}")

    return categories


def extract_card_seller_url(article, ad_url: str, shop_name: str) -> str:
    shop_name_cmp = normalize_for_compare(shop_name)
    best_href = ""
    best_score = 0

    try:
        for anchor in article.query_selector_all("a[href]"):
            href = (anchor.get_attribute("href") or "").strip()
            if not href or href.lower().startswith(("javascript:", "mailto:", "tel:")):
                continue

            absolute_href = normalize_url(href)
            if not absolute_href or absolute_href == ad_url or "/ads/" in absolute_href:
                continue

            text = " ".join([
                (anchor.inner_text() or "").strip().lower(),
                (anchor.get_attribute("title") or "").strip().lower(),
                (anchor.get_attribute("aria-label") or "").strip().lower(),
            ])
            text_cmp = normalize_for_compare(text)

            score = 0
            if shop_name_cmp and shop_name_cmp in text_cmp:
                score += 6
            if any(token in absolute_href.lower() for token in ("/user", "/users", "/profile", "/seller", "/shop", "/store", "/avtomir")):
                score += 4
            if absolute_href.startswith(BASE_URL):
                score += 1
            if len(absolute_href) < len(ad_url):
                score += 1

            if score > best_score:
                best_score = score
                best_href = absolute_href
    except Exception:
        pass

    if best_score >= 4:
        return best_href
    return ""


def collect_pro_links(page: Page) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    debug_entries: list[str] = []

    pro_text_markers = {"premium", "promoted", "featured", "pro"}

    for article in page.query_selector_all("article"):
        try:
            detected_reasons: list[str] = []
            # Quick text snapshot
            try:
                txt = (article.inner_text() or "").strip()
                ltxt = txt.lower()
            except Exception:
                txt = ""
                ltxt = ""

            # 1) Known exact badge/class
            try:
                if article.query_selector(".LFUserAvatar_proLabel__SM0gR"):
                    detected_reasons.append("badge:LFUserAvatar_proLabel__SM0gR")
                if article.query_selector(".LFAdTilePaidFeatures"):
                    detected_reasons.append("badge:LFAdTilePaidFeatures")
            except Exception:
                pass

            # 2) Badge-like elements or attributes
            try:
                # common patterns: data-badge, aria-label, role badges
                if article.query_selector("[data-badge]"):
                    detected_reasons.append("attr:data-badge")
                el = article.query_selector("[aria-label*='pro'], [aria-label*='premium']")
                if el:
                    detected_reasons.append("aria-label badge")
                if article.query_selector(".pro-badge, .ad-badge, .ListingItem_premium, .badge--premium, [class*='PaidFeatures'], [class*='Speaker']"):
                    detected_reasons.append("class:common-badges")
            except Exception:
                pass

            # 3) Explicit badge text in small child nodes only
            try:
                if "🔺" in txt or txt.startswith("🔺"):
                    detected_reasons.append("emoji:triangle")
                for node in article.query_selector_all("span, div, a, p, small, strong, b, i"):
                    node_text = (node.inner_text() or "").strip().lower()
                    if not node_text:
                        continue
                    compact_text = re.sub(r"\s+", " ", node_text)
                    if compact_text in pro_text_markers or compact_text.startswith("🔺premium") or compact_text.startswith("premium"):
                        detected_reasons.append("text:badge")
                        break
            except Exception:
                pass

            # 4) Look into anchor/title/alt attributes
            try:
                for a in article.query_selector_all("a"):
                    title = (a.get_attribute("title") or "").lower()
                    alt = (a.get_attribute("alt") or "").lower()
                    if title in pro_text_markers or alt in pro_text_markers or title.startswith("premium") or alt.startswith("premium") or "🔺premium" in title or "🔺premium" in alt:
                        detected_reasons.append("anchor:title/alt")
                        break
            except Exception:
                pass

            # 5) Class attribute containing keywords
            try:
                classes = " ".join(article.get_attribute("class") or "").lower()
                if any(token in classes for token in ("premium", "pro", "badge", "promoted", "paidfeatures", "speaker")):
                    detected_reasons.append("class:contains-marker")
            except Exception:
                pass

            if not detected_reasons:
                # not identified as PRO
                continue

            # collect first link
            ad_href = ""
            seller_href = ""
            try:
                for a in article.query_selector_all("a"):
                    href = a.get_attribute("href") or ""
                    if href and not href.startswith("javascript") and "/ads/" in href:
                        ad_href = normalize_url(href)
                        break
            except Exception:
                pass

            try:
                seller_href = extract_card_seller_url(article, ad_href, txt)
            except Exception:
                seller_href = ""

            # ad_date collection removed per request

            if ad_href:
                links.append({"ad_url": ad_href, "seller_url": seller_href})

            debug_entries.append(f"{ad_href or '<no-link>'}\t{';'.join(detected_reasons)}\t{(txt[:120].replace('\n',' '))}")

        except Exception:
            continue

    # write debug log to help tune detection
    try:
        with open("pro_detection_debug.txt", "w", encoding="utf-8") as fh:
            for line in debug_entries:
                fh.write(line + "\n")
    except Exception:
        pass

    unique_links: list[dict[str, str]] = []
    seen_ad_urls: set[str] = set()
    for item in links:
        ad_url = item.get("ad_url", "")
        if ad_url and ad_url not in seen_ad_urls:
            seen_ad_urls.add(ad_url)
            unique_links.append(item)

    return unique_links


def extract_profile_url(page: Page, page_source: str, current_url: str, shop_name: str) -> str:
    shop_name_lc = normalize_shop_name(shop_name)

    regex_patterns = [
        r'"public_url":\s*"([^\"]+)"',
        r'"profile_url":\s*"([^\"]+)"',
        r'"seller_url":\s*"([^\"]+)"',
        r'"user_url":\s*"([^\"]+)"',
    ]
    for pattern in regex_patterns:
        match = re.search(pattern, page_source)
        if match:
            candidate = normalize_url(match.group(1).strip())
            if candidate and candidate != current_url and "/ads/" not in candidate:
                return candidate

    best_href = ""
    best_score = 0
    try:
        for anchor in page.query_selector_all("a[href]"):
            href = (anchor.get_attribute("href") or "").strip()
            if not href or href.lower().startswith(("javascript:", "mailto:", "tel:")):
                continue

            absolute_href = normalize_url(href)
            if not absolute_href or absolute_href == current_url or "/ads/" in absolute_href:
                continue

            text_bits = [
                (anchor.inner_text() or "").strip().lower(),
                (anchor.get_attribute("title") or "").strip().lower(),
                (anchor.get_attribute("aria-label") or "").strip().lower(),
            ]
            combined_text = " ".join(bit for bit in text_bits if bit)

            score = 0
            if shop_name_lc and shop_name_lc in combined_text:
                score += 5
            if absolute_href.startswith(BASE_URL) and absolute_href != BASE_URL:
                score += 1
            if any(token in absolute_href.lower() for token in ("/user", "/users", "/profile", "/seller", "/shop", "/store")):
                score += 4
            if len(absolute_href) < len(current_url):
                score += 1
            if combined_text and len(combined_text) <= 80:
                score += 1

            if score > best_score:
                best_score = score
                best_href = absolute_href
    except Exception:
        pass

    if best_score >= 4:
        return best_href

    return ""


def extract_mobile_numbers(page: Page, page_source: str, body_text: str) -> list[str]:
    candidates: list[str] = []

    try:
        for selector in ["main a[href^='tel:']", "article a[href^='tel:']", "section a[href^='tel:']", "a[href^='tel:']"]:
            anchors = page.query_selector_all(selector)
            if anchors:
                for anchor in anchors:
                    href = (anchor.get_attribute("href") or "").strip()
                    if href.lower().startswith("tel:"):
                        candidates.append(href[4:])
                    text = (anchor.inner_text() or "").strip()
                    if text:
                        candidates.append(text)
                break
    except Exception:
        pass

    if not candidates:
        combined_text = f"{page_source}\n{body_text}"
        tel_matches = re.findall(r"tel:(?:\+994|994)[\d\s\-\(\)]{7,}\d", combined_text, flags=re.IGNORECASE)
        if tel_matches:
            candidates.extend([match.split("tel:", 1)[1] for match in tel_matches])
        else:
            fallback_matches = re.findall(r"(?<!\d)(?:\+994|994)[\d\s\-\(\)]{7,}\d", combined_text)
            candidates.extend(fallback_matches)

    mobile_numbers: list[str] = []
    for candidate in candidates:
        normalized = normalize_mobile_number(candidate)
        if normalized:
            mobile_numbers.append(normalized)

    return unique_texts(mobile_numbers)


def click_contact_buttons(page: Page) -> None:
    # Try button texts that reveal contact info (phone or email)
    contact_tokens = ("göst", "gost", "nomr", "nömr", "nomre", "telefon", "elaqe", "elaqə", "contact", "e-mail", "email", "mail")
    for button in page.query_selector_all("button"):
        try:
            text = (button.inner_text() or "").lower()
            aria = (button.get_attribute("aria-label") or "").lower()
            if any(token in text for token in contact_tokens) or any(token in aria for token in contact_tokens):
                button.scroll_into_view_if_needed()
                try:
                    button.click()
                except Exception:
                    try:
                        page.evaluate("el => el.click()", button)
                    except Exception:
                        pass
                page.wait_for_timeout(900)
                return
        except Exception:
            continue

    # As a fallback, try clicking anchor-like elements that might reveal contacts
    for a in page.query_selector_all("a"):
        try:
            href = (a.get_attribute("href") or "").lower()
            text = (a.inner_text() or "").lower()
            if href.startswith("mailto:") or any(token in text for token in ("email", "e-mail", "mail", "contact", "elaqe", "elaqə")):
                try:
                    a.scroll_into_view_if_needed()
                except Exception:
                    pass
                # don't actually navigate away on mailto; just ensure it's present
                page.wait_for_timeout(300)
                return
        except Exception:
            continue


def normalize_mobile_number(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if digits.startswith("994"):
        local_part = digits[3:]
        if len(local_part) == 9 and local_part[:2] in {"50", "51", "55", "70", "77", "99"}:
            return f"+994{local_part}"
    return ""


def extract_shop_data(page: Page, page_source: str, body_text: str, current_url: str, category: str = "") -> dict[str, Any]:
    seller_id = ""
    for pattern in [r'"user_id":\s*(\d+)', r'"user":\{"id":\s*(\d+)']:
        m = re.search(pattern, page_source)
        if m:
            seller_id = m.group(1)
            break

    shop_name = ""
    for pattern in [r'"username":"([^\"]+)"', r'"company_name":"([^\"]+)"', r'<span class="LFUserAvatar_userNameText__hVTqv">([^<]+)</span>']:
        m = re.search(pattern, page_source)
        if m:
            shop_name = m.group(1).strip()
            break

    mobile_numbers = extract_mobile_numbers(page, page_source, body_text)

    profile_url = extract_profile_url(page, page_source, current_url, shop_name)

    if not profile_url and current_url and "/ads/" not in current_url:
        profile_url = current_url

    # shop_since extraction removed (field was empty for most sellers)

    extracted_category = ""
    for pattern in [r'"category":\s*"([^\"]+)"', r'"category_name":\s*"([^\"]+)"', r'"parent_category":\s*"([^\"]+)"']:
        m = re.search(pattern, page_source)
        if m:
            extracted_category = m.group(1).strip()
            if extracted_category and extracted_category.lower() not in {"null", ""}:
                break

    if not extracted_category:
        try:
            url_match = re.search(r'/ads/([^/]+)-id-\d+', current_url)
            if url_match:
                ad_title = url_match.group(1).replace('-', ' ')
                words = [w.title() for w in ad_title.split() if w and len(w) > 2][:2]
                if words:
                    extracted_category = ' '.join(words)
        except Exception:
            pass

    final_category = extracted_category or category or "Bilinmir"
    if final_category.lower() == "bütün elanlar" and extracted_category:
        final_category = extracted_category

    return {
        "seller_id": seller_id,
        "shop_name": shop_name,
        "shop_url": profile_url,
        "mobile_numbers": mobile_numbers,
        "category": final_category,
    }


def crawl_category(page: Page, category_name: str, category_url: str) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    try:
        print(f"\n🔍 Kateqoriya açılır: {category_name}")
        focus_browser(page)

        # Navigate to the category first
        resp = page.goto(category_url, timeout=30000)
        if resp is not None and resp.status == 404:
            with open("failed_urls.txt", "a", encoding="utf-8") as f:
                f.write(f"{category_url}\n")
            print(f"  ⚠ {category_url} -> 404, atlandi")
            return results

        page.wait_for_timeout(1500)

        # Collect PRO ad links across multiple pages / load-more interactions
        seen_ads: set[str] = set()
        all_pro_links: list[dict[str, str]] = []
        consecutive_empty = 0

        for page_index in range(1, MAX_PAGES_PER_CATEGORY + 1):
            print(f"  ▶ Səhifə işlənir: {page_index}/{MAX_PAGES_PER_CATEGORY}")
            # On first iteration we are already on page 1; on subsequent iterations try to load more
            if page_index > 1:
                loaded = False
                # Try common load-more buttons
                try:
                    selectors = [
                        "button:has-text(\"Daha çox\")",
                        "button:has-text(\"Daha\")",
                        "button:has-text(\"Load more\")",
                        ".load-more",
                        ".LoadMoreButton",
                        ".button_load_more",
                        "button[data-test=load-more]",
                    ]
                    for sel in selectors:
                        try:
                            btn = page.query_selector(sel)
                            if btn:
                                try:
                                    btn.scroll_into_view_if_needed()
                                    btn.click()
                                    page.wait_for_timeout(1500)
                                    loaded = True
                                    break
                                except Exception:
                                    try:
                                        page.evaluate("el => el.click()", btn)
                                        page.wait_for_timeout(1500)
                                        loaded = True
                                        break
                                    except Exception:
                                        continue
                        except Exception:
                            continue
                except Exception:
                    loaded = False

                # If no load-more button, try 'next' pagination link
                if not loaded:
                    try:
                        next_link = page.query_selector('a[rel="next"], .pagination a.next')
                        if next_link:
                            href = next_link.get_attribute("href") or ""
                            if href:
                                page.goto(normalize_url(href), timeout=30000)
                                page.wait_for_timeout(1500)
                                loaded = True
                    except Exception:
                        loaded = False

                # Fallback: try URL with ?page=N or &page=N
                if not loaded:
                    try:
                        if "?" in category_url:
                            next_url = f"{category_url}&page={page_index}"
                        else:
                            next_url = f"{category_url}?page={page_index}"
                        resp = page.goto(next_url, timeout=30000)
                        if resp is not None and resp.status == 404:
                            # stop if pages produce 404
                            break
                        page.wait_for_timeout(1500)
                        loaded = True
                    except Exception:
                        pass

            # Scroll and collect
            scroll_to_bottom(page)
            pro_links = collect_pro_links(page)

            # Filter new links
            new_links = [item for item in pro_links if item.get("ad_url") and item.get("ad_url") not in seen_ads]
            if new_links:
                consecutive_empty = 0
                for item in new_links:
                    ad_url = item.get("ad_url", "")
                    if ad_url:
                        seen_ads.add(ad_url)
                        all_pro_links.append(item)
            else:
                consecutive_empty += 1

            # Stop if we've seen no new links for several pages
            if consecutive_empty >= CONSECUTIVE_EMPTY_PAGES_TO_STOP:
                break

        if not all_pro_links:
            print(f"  ℹ {category_name} kateqoriyasında PRO kart tapılmadı")
            return results

        print(f"  ✓ {len(all_pro_links)} PRO elan tapıldı")

        # Visit each seller page and extract seller info
        for index, item in enumerate(all_pro_links, 1):
            try:
                ad_url = item.get("ad_url", "")
                seller_page_url = item.get("seller_url", "")
                if not seller_page_url:
                    # We only want the seller page flow; skip cards where we could not derive one.
                    continue
                focus_browser(page)
                resp = page.goto(seller_page_url, timeout=30000)
                if resp is not None and resp.status == 404:
                    with open("failed_urls.txt", "a", encoding="utf-8") as f:
                        f.write(f"{seller_page_url}\n")
                    print(f"  ⚠ {seller_page_url} -> 404, atlandi")
                    continue
                page.wait_for_timeout(DELAY_BETWEEN_ADS * 1000)
                click_contact_buttons(page)

                page_source = page.content()
                body_text = page.inner_text("body") or ""
                shop_data = extract_shop_data(page, page_source, body_text, page.url, category_name)

                seller_key = canonical_seller_key(shop_data["seller_id"], shop_data["shop_url"], shop_data["shop_name"]) or ad_url
                seller = results.setdefault(
                    seller_key,
                    {
                        "seller_id": seller_key,
                        "shop_name": "",
                        "shop_url": shop_data["shop_url"],
                        "mobile_numbers": [],
                        "categories": [],
                        "ads_count": 0,
                        "ad_urls": [],
                    },
                )

                if ad_url not in seller["ad_urls"]:
                    seller["ad_urls"].append(ad_url)
                # ad_date handling removed
                seller["ads_count"] = len(seller["ad_urls"])
                if shop_data["shop_name"] and not seller["shop_name"]:
                    seller["shop_name"] = shop_data["shop_name"]
                if shop_data["shop_url"] and not seller["shop_url"]:
                    seller["shop_url"] = shop_data["shop_url"]

                seller["mobile_numbers"] = unique_texts([*seller["mobile_numbers"], *shop_data["mobile_numbers"]])

                # Aggregate categories per seller avoiding duplicates
                if shop_data["category"] and shop_data["category"] not in seller["categories"]:
                    seller["categories"].append(shop_data["category"])
                elif category_name and category_name not in seller["categories"]:
                    seller["categories"].append(category_name)

                print(f"  {index}/{len(all_pro_links)} TAPILDI: {seller['shop_name'] or seller['shop_url'] or ad_url}")

            except Exception as e:
                print(f"  ⚠ {ad_url} oxunması xətası: {e}")
                continue

        page.wait_for_timeout(DELAY_BETWEEN_CATEGORIES * 1000)

    except Exception as e:
        print(f"⚠ {category_name} kateqoriyası xətası: {e}")

    return results


def merge_results(all_results: list[dict[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for category_results in all_results:
        for seller_key, seller_data in category_results.items():
            if seller_key not in merged:
                merged[seller_key] = seller_data
            else:
                existing = merged[seller_key]
                existing["ad_urls"] = unique_texts([*existing.get("ad_urls", []), *seller_data.get("ad_urls", [])])
                existing["ads_count"] = int(existing.get("ads_count", 0)) + int(seller_data.get("ads_count", 0))
                existing["mobile_numbers"] = unique_texts([*existing["mobile_numbers"], *seller_data["mobile_numbers"]])
                existing["categories"] = unique_texts([*existing["categories"], *seller_data["categories"]])
                if seller_data["shop_url"] and not existing["shop_url"]:
                    existing["shop_url"] = seller_data["shop_url"]

    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description="Lalafo Playwright parser")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--headed", action="store_true", help="Run browser with UI (headed)")
    mode.add_argument("--headless", action="store_true", help="Run browser without UI (headless)")
    parser.add_argument("--all", action="store_true", help="Crawl all pages for every discovered category and write per-category JSONs + combined JSON/XLSX")
    parser.add_argument("--category", type=str, help="Only crawl the named category (case-insensitive)")
    args = parser.parse_args()
    headless = args.headless and not args.headed

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        # Create a context with a common User-Agent to reduce 404s caused by bot blocking
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
        context = browser.new_context(user_agent=user_agent, viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # If headed, bring the Playwright page to the front so you can watch actions
        if not headless:
            try:
                page.bring_to_front()
            except Exception:
                pass

        try:
            print("📥 Lalafo əsas səhifəsi açılır...")
            page.goto(BASE_URL, timeout=30000)
            page.wait_for_timeout(2000)
            # Save rendered homepage HTML for debugging discovered links
            try:
                with open("homepage_content.html", "w", encoding="utf-8") as hf:
                    hf.write(page.content() or "")
            except Exception:
                pass

            categories = get_categories(page)

            if not categories:
                print("⚠ Kateqoriyalar aşkar edilə bilmədi, əsas səhifədən PRO-lar çəkilir...")
                categories = {"Bütün Elanlar": BASE_URL}
            else:
                print(f"✓ {len(categories)} kateqoriya tapıldı: {', '.join(categories.keys())}")

            # If a specific category was requested, filter to just that one (case-insensitive match or substring)
            if args.category:
                requested = args.category.strip().lower()
                found = None
                for name, url in categories.items():
                    if name.strip().lower() == requested:
                        found = (name, url)
                        break
                if not found:
                    for name, url in categories.items():
                        if requested in name.strip().lower():
                            found = (name, url)
                            break
                if found:
                    categories = {found[0]: found[1]}
                    print(f"ℹ Sadəcə seçilmiş kateqoriya işlənəcək: {found[0]}")
                else:
                    # If the user supplied a path or URL, accept it
                    if requested.startswith("/") or requested.startswith("http"):
                        categories = {args.category: normalize_url(args.category)}
                        print(f"ℹ Verilən yol üzrə kateqoriya işlənəcək: {args.category}")
                    else:
                        print(f"⚠ Kateqoriya '{args.category}' tapılmadı; mövcud kateqoriyalar: {', '.join(categories.keys())}")
                        return

            all_results: list[dict[str, dict[str, Any]]] = []
            if args.all:
                # temporarily lift page limit to crawl all pages
                global MAX_PAGES_PER_CATEGORY
                old_max = MAX_PAGES_PER_CATEGORY
                MAX_PAGES_PER_CATEGORY = 9999
                try:
                    for cat_name, cat_url in categories.items():
                        cat_results = crawl_category(page, cat_name, cat_url)
                        if not cat_results:
                            print(f"  ℹ {cat_name} üçün nəticə tapılmadı")
                            continue
                        # write per-category JSON
                        sellers_output = []
                        for seller in cat_results.values():
                            scopy = dict(seller)
                            scopy.pop("ad_urls", None)
                            sellers_output.append(scopy)
                        perfile = f"lalafo_{slugify_filename(cat_name)}.json"
                        with open(perfile, "w", encoding="utf-8") as fh:
                            json.dump({"source": BASE_URL, "category": cat_name, "sellers": sorted(sellers_output, key=lambda item: (item.get("shop_name") or "").lower())}, fh, ensure_ascii=False, indent=4)
                        print(f"  ✅ Yazıldı: {perfile}")
                        all_results.append(cat_results)
                finally:
                    MAX_PAGES_PER_CATEGORY = old_max

                # merge all category results and write combined JSON + XLSX
                merged = merge_results(all_results)
                if not merged:
                    print("\n⚠ Heç bir PRO satıcı tapılmadı!")
                    return

                # write combined JSON
                combined_rows = sorted([{k: v for k, v in s.items() if k != 'ad_urls'} for s in merged.values()], key=lambda item: (item.get("shop_name") or "").lower())

                combined_json = {
                    "source": BASE_URL,
                    "total_pro_sellers": len(merged),
                    "categories_crawled": list(categories.keys()),
                    "sellers": combined_rows,
                }
                with open("all_lalafo.json", "w", encoding="utf-8") as fh:
                    json.dump(combined_json, fh, ensure_ascii=False, indent=4)
                print(f"\n✅ Birləşmiş JSON yazıldı: all_lalafo.json")

                # write combined Excel workbook
                xlsx_file = "all_lalafo.xlsx"
                export_xlsx(combined_rows, xlsx_file)
                print(f"✅ Birləşmiş Excel yazıldı: {xlsx_file}")
                return
            else:
                # default behavior: existing single-category or single-run flow
                all_results = []
                for cat_name, cat_url in categories.items():
                    cat_results = crawl_category(page, cat_name, cat_url)
                    if cat_results:
                        all_results.append(cat_results)

                merged = merge_results(all_results)

                if not merged:
                    print("\n⚠ Heç bir PRO satıcı tapılmadı!")
                    return

                sellers_output = []
                for seller in merged.values():
                    seller_copy = dict(seller)
                    seller_copy.pop("ad_urls", None)
                    sellers_output.append(seller_copy)

                output = {
                    "source": BASE_URL,
                    "total_pro_sellers": len(merged),
                    "categories_crawled": list(categories.keys()),
                    "sellers": sorted(sellers_output, key=lambda item: (item.get("shop_name") or "").lower()),
                }

                with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
                    json.dump(output, file, ensure_ascii=False, indent=4)

                print(f"\n✅ JSON HAZIRDIR: {OUTPUT_FILE}")
                print(f"📊 TOPLAM MAGAZA: {len(merged)}")
                print("\nÖrnək satıcılar:")
                for seller in list(merged.values())[:5]:
                    cats_text = f" | Kateqoriyalar: {', '.join(seller.get('categories', []))}" if seller.get('categories') else ""
                    print(f"  - {seller['shop_name']}{cats_text}")

        finally:
            try:
                browser.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()


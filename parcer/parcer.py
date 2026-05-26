from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://tap.az"
DEFAULT_HEADERS = {
	"User-Agent": (
		"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
		"(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
	),
	"Accept-Language": "az-AZ,az;q=0.9,en;q=0.8,tr;q=0.7",
}

CATEGORY_NAME_MAP = {
	"neqliyyat": "Nəqliyyat",
	"elektronika": "Elektronika",
	"ev-ve-bag-ucun": "Ev və bağ üçün",
	"ehtiyat-hisseleri-ve-aksesuarlar": "Ehtiyat hissələri və aksesuarlar",
	"dasinmaz-emlak": "Daşınmaz əmlak",
	"xidmetler-ve-biznes": "Xidmətlər və biznes",
	"sexsi-esyalar": "Şəxsi əşyalar",
	"hobbi-ve-asude": "Hobbi və asudə",
	"meiset-texnikasi": "Məişət texnikası",
	"usaq-alemi": "Uşaq aləmi",
	"heyvanlar": "Heyvanlar",
	"is-elanlari": "İş elanları",
}

if hasattr(sys.stdout, "reconfigure"):
	sys.stdout.reconfigure(encoding="utf-8")

# Bu modul `tap.az` saytından elan məlumatlarını çəkmək üçün nəzərdə tutulub.
# Aşağıda dataclass-lar nəticə strukturunu saxlayır, sonra isə HTTP sessiya,
# parsing (kateqoriya və detail səhifələri) və nəticəni JSON/CSV-ə yazan
# köməkçi funksiyalar ardıcıl olaraq verilib.


@dataclass
class ListingSummary:
	url: str
	ad_id: str | None = None
	title: str | None = None
	price: str | None = None
	description: str | None = None
	location: str | None = None
	seller_type: str | None = None
	is_store: bool = False
	time_text: str | None = None
	raw_text: str | None = None
	phone_numbers: list[str] = field(default_factory=list)


@dataclass

class ListingDetail(ListingSummary):
	category: str | None = None
	attributes: dict[str, str] = field(default_factory=dict)
	image_urls: list[str] = field(default_factory=list)
	seller_name: str | None = None
	source_url: str | None = None


def create_session() -> requests.Session:
	# HTTP sessiyası yaradılır və modul səviyyəli başlıqlar (`DEFAULT_HEADERS`) əlavə olunur.
	session = requests.Session()
	session.headers.update(DEFAULT_HEADERS)
	return session


def fetch_html(session: requests.Session, url: str, timeout: int = 30) -> str:
	# URL-dən HTML məzmunu götürür, status yoxlanılır və uyğun kodlaşdırma tətbiq edilir.
	response = session.get(url, timeout=timeout)
	response.raise_for_status()
	response.encoding = response.apparent_encoding or response.encoding or "utf-8"
	return response.text


def normalize_text(value: str | None) -> str | None:
	if value is None:
		return None
	# Yığışdırma: çoxlu boşluqları tək boşluğa çevirir və iki tərəfi trim edir.
	value = re.sub(r"\s+", " ", value).strip()
	return value or None


def unique(values: Iterable[str]) -> list[str]:
	seen: set[str] = set()
	result: list[str] = []
	for value in values:
		value = value.strip()
		if not value or value in seen:
			continue
		seen.add(value)
		result.append(value)
	return result


def extract_ad_id(url: str) -> str | None:
	match = re.search(r"/(\d+)(?:\D*)?$", url)
	return match.group(1) if match else None


def extract_category_name(page_url: str) -> str | None:
	parsed = urlparse(page_url)
	parts = [part for part in parsed.path.split("/") if part]
	if len(parts) < 2 or parts[0] != "elanlar":
		return None
	category_slug = parts[1]
	return CATEGORY_NAME_MAP.get(category_slug, normalize_text(category_slug.replace("-", " ").replace("_", " ").title()))


def parse_price(text: str | None) -> str | None:
	if not text:
		return None
	match = re.search(r"(\d[\d\s.]*(?:[\.,]\d+)?)\s*AZN", text, re.IGNORECASE)
	if match:
		return normalize_text(match.group(1) + " AZN")
	return None


def strip_card_noise(source: str | None) -> str | None:
	if not source:
		return None
	text = re.sub(r'^(Mağaza|Şəxsi)\b', '', source)
	text = re.sub(r"\b\d[\d\s.]*?(?:[\.,]\d+)?\s*AZN\b", "", text, flags=re.IGNORECASE)
	text = re.sub(r"\b(Bakı|Sumqayıt|Gəncə|Xırdalan|Lənkəran|Şəki|Mingəçevir|Naxçıvan)\b,?", "", text)
	return normalize_text(text)


def parse_listing_card(anchor) -> ListingSummary:
	href = urljoin(BASE_URL, anchor.get("href", ""))
	text = normalize_text(anchor.get_text(" ", strip=True))
	title_attr = normalize_text(anchor.get("title"))
	ad_id = extract_ad_id(href)

	raw_text = text

	# Choose title: explicit attribute first, otherwise cleaned visible text.
	title = title_attr or strip_card_noise(text)

	price = parse_price(text or title)
	description = strip_card_noise(text)
	seller_type = None
	if text and "Mağaza" in text:
		seller_type = "Mağaza"
	elif text and "Şəxsi" in text:
		seller_type = "Şəxsi"

	is_store = seller_type == "Mağaza" or (text is not None and "Mağaza" in text)

	location = None
	time_text = None
	if text:
		# split on commas with optional whitespace to robustly find location
		parts = [part.strip() for part in re.split(r"\s*,\s*", text) if part.strip()]
		if len(parts) > 1:
			# last part commonly contains city or region, strip trailing commas
			location = parts[-1].rstrip(",")
		if "Bu gün" in text or "Dünən" in text:
			time_match = re.search(r"(Bu gün|Dünən)[^\d]*(\d{1,2}:\d{2})", text)
			if time_match:
				time_text = normalize_text(" ".join(time_match.groups()))

	return ListingSummary(
		url=href,
		ad_id=ad_id,
		title=title,
		price=price,
		description=description,
		location=location,
		seller_type=seller_type,
		is_store=is_store,
		time_text=time_text,
		raw_text=raw_text,
	)


def find_listing_anchors(soup: BeautifulSoup) -> list[Any]:
	anchors = []
	for anchor in soup.find_all("a", href=True):
		href = anchor["href"]
		if "/elanlar/" not in href:
			continue
		if re.search(r"/\d+(?:[/?#].*)?$", href) is None:
			continue
		anchors.append(anchor)
	return anchors


def parse_category_page(html: str, page_url: str) -> tuple[list[ListingSummary], str | None]:
	soup = BeautifulSoup(html, "lxml")
	cards: list[ListingSummary] = []
	seen: set[str] = set()

	for anchor in find_listing_anchors(soup):
		href = urljoin(page_url, anchor.get("href", ""))
		ad_id = extract_ad_id(href)
		if not ad_id or ad_id in seen:
			continue
		seen.add(ad_id)

		card = parse_listing_card(anchor)
		if card.title or card.price:
			cards.append(card)

	next_link = soup.find("a", rel=lambda value: value and "next" in value.lower())
	if next_link and next_link.get("href"):
		return cards, urljoin(page_url, next_link["href"])

	for candidate in soup.find_all("a", href=True):
		text = normalize_text(candidate.get_text(" ", strip=True)) or ""
		if text in {"Növbəti", "Next", "Sonrakı"}:
			return cards, urljoin(page_url, candidate["href"])

	return cards, None


def extract_meta_content(soup: BeautifulSoup, *, property_name: str | None = None, name: str | None = None) -> str | None:
	selector = None
	if property_name:
		selector = f'meta[property="{property_name}"]'
	elif name:
		selector = f'meta[name="{name}"]'
	if not selector:
		return None
	tag = soup.select_one(selector)
	if not tag:
		return None
	return normalize_text(tag.get("content"))


def parse_attributes_from_soup(soup: BeautifulSoup) -> dict[str, str]:
	attributes: dict[str, str] = {}

	for row in soup.select("table tr"):
		cells = [normalize_text(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
		cells = [cell for cell in cells if cell]
		if len(cells) >= 2:
			attributes.setdefault(cells[0], cells[1])

	for item in soup.select("dl > div, dl > li, .parameters li, .item-params li"):
		texts = [normalize_text(part) for part in item.stripped_strings]
		texts = [text for text in texts if text]
		if len(texts) >= 2:
			attributes.setdefault(texts[0], texts[1])

	return attributes


def parse_phone_numbers(html: str) -> list[str]:
	candidates: list[str] = []
	soup = BeautifulSoup(html, "lxml")
	phone_scope_selectors = [
		".gallery-phones-dropdown",
		".product-phones",
		".phone-numbers",
	]
	phone_scopes = []
	for selector in phone_scope_selectors:
		phone_scopes.extend(soup.select(selector))

	def _add_candidate(value: str | None) -> None:
		if not value:
			return
		candidates.append(value)

	for scope in phone_scopes:
		for anchor in scope.select('a[href^="tel:"]'):
			_add_candidate(anchor.get("href", "").removeprefix("tel:"))
			_add_candidate(anchor.get_text(" ", strip=True))
		for match in re.finditer(r"(?:\+?994|0)?(?:\s*\(?\d{2,3}\)?\s*)\d[\d\s().-]{6,}\d", scope.get_text(" ", strip=True)):
			_add_candidate(match.group(0))

	if not candidates:
		for anchor in soup.select('a[href^="tel:"]'):
			parent_classes = " ".join(
				" ".join(parent.get("class", []))
				for parent in anchor.parents
				if getattr(parent, "attrs", None)
			)
			if re.search(r"contact-us|burger-menu__section--social", parent_classes, flags=re.IGNORECASE):
				continue
			_add_candidate(anchor.get("href", "").removeprefix("tel:"))
			_add_candidate(anchor.get_text(" ", strip=True))

	if not candidates:
		for match in re.finditer(r"(?:\+?994|0)(?:\s*\(?\d{2,3}\)?\s*)\d[\d\s().-]{6,}\d", html):
			_add_candidate(match.group(0))

	excluded_digits = {
		"0125261919",
		"994125261919",
	}
	cleaned = []
	seen_phone_digits: set[str] = set()
	for value in candidates:
		value = normalize_text(value)
		if not value:
			continue
		value = re.sub(r"^tel:", "", value, flags=re.IGNORECASE)
		value = value.replace("(", "").replace(")", "")
		value = re.sub(r"\s+", " ", value).strip()
		digits = re.sub(r"\D", "", value)
		if len(digits) not in {10, 12}:
			continue
		if len(digits) == 12 and not digits.startswith("994"):
			continue
		if len(digits) == 10 and not digits.startswith("0"):
			continue
		if digits in excluded_digits:
			continue
		if len(digits) == 10 and digits[1] not in {"1", "5", "6", "7", "9"}:
			continue
		if digits in seen_phone_digits:
			continue
		seen_phone_digits.add(digits)
		cleaned.append(value)

	return unique(cleaned)


def parse_listing_detail(html: str, page_url: str) -> ListingDetail:
	soup = BeautifulSoup(html, "lxml")

	title = extract_meta_content(soup, property_name="og:title")
	if not title:
		title_tag = soup.find("h1")
		title = normalize_text(title_tag.get_text(" ", strip=True)) if title_tag else None

	description = extract_meta_content(soup, name="description")
	price = extract_meta_content(soup, property_name="product:price:amount")
	if price:
		price = normalize_text(price + " AZN") if "AZN" not in price else price
	if not price and title:
		price = parse_price(title)

	image_urls = []
	for meta in soup.select('meta[property="og:image"], meta[property="og:image:secure_url"]'):
		content = normalize_text(meta.get("content"))
		if content:
			image_urls.append(content)
	for img in soup.find_all("img", src=True):
		src = img.get("src")
		if src and "tap.az" in src:
			image_urls.append(urljoin(page_url, src))
	image_urls = unique(image_urls)

	phone_numbers = parse_phone_numbers(html)
	attributes = parse_attributes_from_soup(soup)

	seller_name = None
	# Try to extract from JSON-LD schema
	for script in soup.find_all("script", type="application/ld+json"):
		try:
			data = json.loads(script.string)
			if isinstance(data, dict) and "offers" in data:
				offers = data["offers"]
				if isinstance(offers, dict) and "seller" in offers:
					seller = offers["seller"]
					if isinstance(seller, dict) and "name" in seller:
						seller_name = normalize_text(seller["name"])
						if seller_name:
							break
			elif isinstance(data, list):
				for item in data:
					if isinstance(item, dict) and "offers" in item:
						offers = item["offers"]
						if isinstance(offers, dict) and "seller" in offers:
							seller = offers["seller"]
							if isinstance(seller, dict) and "name" in seller:
								seller_name = normalize_text(seller["name"])
								if seller_name:
									break
		except (json.JSONDecodeError, TypeError):
			continue
	
	# Fallback: try to find seller name in text
	if not seller_name:
		seller_blocks = soup.find_all(string=re.compile(r"(?:Satıcı|Seller)[:：\s]+", re.IGNORECASE))
		if seller_blocks:
			text = normalize_text(str(seller_blocks[0]))
			# Remove the "Satıcı:" or "Seller:" prefix
			seller_name = re.sub(r"^(?:Satıcı|Seller)[:：\s]+", "", text, flags=re.IGNORECASE).strip()
			if not seller_name:
				seller_name = None

	seller_type = "Mağaza" if (title and "Mağaza" in title) or (description and "Mağaza" in description) else None
	if not seller_type:
		full_text = soup.get_text(" ", strip=True)
		if "Mağaza" in full_text:
			seller_type = "Mağaza"
		elif "Şəxsi" in full_text:
			seller_type = "Şəxsi"

	ad_id = extract_ad_id(page_url)
	location = None
	location_match = re.search(r"([A-ZƏÖÜÇĞŞİ][^,]+),\s*(Bakı|Sumqayıt|Gəncə|Xırdalan|Lənkəran|Şəki|Mingəçevir|Naxçıvan)", html)
	if location_match:
		raw_loc = location_match.group(0)
		# Strip any HTML that may have been captured by the regex
		loc_text = BeautifulSoup(raw_loc, "lxml").get_text(" ", strip=True)
		location = normalize_text(loc_text)

	return ListingDetail(
		url=page_url,
		source_url=page_url,
		ad_id=ad_id,
		title=title,
		price=price,
		location=location,
		seller_type=seller_type,
		is_store=seller_type == "Mağaza",
		raw_text=None,
		description=description,
		category=extract_category_name(page_url),
		attributes=attributes,
		phone_numbers=phone_numbers,
		image_urls=image_urls,
		seller_name=seller_name,
	)


def scrape_category(session: requests.Session, url: str, pages: int = 1, store_only: bool = False) -> list[ListingSummary]:
	results: list[ListingSummary] = []
	current_url = url

	page_count = 0
	# pages == 0 means unlimited: keep following "next" until there's no next page.
	while True:
		if pages > 0 and page_count >= pages:
			break

		html = fetch_html(session, current_url)
		page_items, next_url = parse_category_page(html, current_url)

		for item in page_items:
			if store_only and not item.is_store:
				continue
			results.append(item)

		page_count += 1
		if not next_url:
			break
		current_url = next_url

	return results


def scrape_detail(session: requests.Session, url: str) -> ListingDetail:
	html = fetch_html(session, url)
	return parse_listing_detail(html, url)


def discover_categories(session: requests.Session) -> list[dict[str, str]]:
	return [
		{"title": title, "url": urljoin(BASE_URL, f"/elanlar/{slug}")}
		for slug, title in CATEGORY_NAME_MAP.items()
	]


def to_json(data: Any) -> str:
	return json.dumps(data, ensure_ascii=False, indent=2)


def write_csv(data: Any, file_path: str) -> None:
	rows: list[dict[str, Any]]
	if isinstance(data, dict):
		rows = [data]
	else:
		rows = list(data)

	if not rows:
		with open(file_path, "w", encoding="utf-8-sig", newline="") as file:
			file.write("")
		return

	fieldnames: list[str] = []
	seen: set[str] = set()
	for row in rows:
		if not isinstance(row, dict):
			continue
		for key in row.keys():
			if key not in seen:
				seen.add(key)
				fieldnames.append(key)

	with open(file_path, "w", encoding="utf-8-sig", newline="") as file:
		writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
		writer.writeheader()
		for row in rows:
			if not isinstance(row, dict):
				continue
			flat_row: dict[str, Any] = {}
			for key, value in row.items():
				if isinstance(value, (list, dict)):
					flat_row[key] = json.dumps(value, ensure_ascii=False)
				elif value is None:
					flat_row[key] = ""
				else:
					flat_row[key] = value
			writer.writerow(flat_row)


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Tap.az parser for ads, categories and store listings")
	parser.add_argument("--url", help="Parse a Tap.az ad or category URL")
	parser.add_argument("--category", help="Alias for --url when parsing a category page")
	parser.add_argument("--detail", action="store_true", help="Force detail-page parsing")
	parser.add_argument("--pages", type=int, default=1, help="How many category pages to scrape (use 0 for unlimited)")
	parser.add_argument("--store-only", action="store_true", help="Keep only store listings")
	parser.add_argument("--fetch-details", action="store_true", help="Kept for compatibility; category scraping now fetches details by default")
	parser.add_argument("--discover-categories", action="store_true", help="List available category links from the homepage")
	parser.add_argument("--group-by-store", action="store_true", help="Group results by store name")
	parser.add_argument("--store", help="Filter results by store name (simpler syntax)")
	parser.add_argument("--cat", help="Filter results by category (use with --store)")
	parser.add_argument("--filter-store", help="Filter results by store name")
	parser.add_argument("--filter-category", help="Filter results by category (use with --filter-store)")
	parser.add_argument("--json", action="store_true", help="Print JSON output")
	parser.add_argument("--csv", action="store_true", help="Save the result as CSV")
	parser.add_argument("--output", help="Save the result to a file")
	return parser


def is_detail_url(url: str) -> bool:
	parsed = urlparse(url)
	return bool(re.search(r"/\d+(?:[/?#].*)?$", parsed.path))


def group_by_store(data: list[dict[str, Any]]) -> dict[str, Any]:
	"""Group listings by store name/seller_name"""
	stores: dict[str, dict[str, Any]] = {}
	
	for item in data:
		# Get store identifier from seller_name or seller_type
		store_name = item.get("seller_name") or item.get("seller_type") or "Bilinməmiş mağaza"
		
		# Initialize store if not seen before
		if store_name not in stores:
			stores[store_name] = {
				"magaza_adi": store_name,
				"mehsullar": []
			}
		
		# Add product to store
		stores[store_name]["mehsullar"].append(item)
	
	# Convert to list format maintaining order
	return {"magazalar": list(stores.values())}


def filter_by_store(data: list[dict[str, Any]], store_name: str) -> list[dict[str, Any]]:
	"""Filter products by store name (case-insensitive partial match)"""
	store_name_lower = store_name.lower()
	return [
		item for item in data
		if store_name_lower in (item.get("seller_name") or "").lower()
		or store_name_lower in (item.get("seller_type") or "").lower()
	]


def filter_by_store_and_category(
	data: list[dict[str, Any]], 
	store_name: str, 
	category_name: str
) -> list[dict[str, Any]]:
	"""Filter products by store name and category (case-insensitive)"""
	store_name_lower = store_name.lower()
	category_name_lower = category_name.lower()
	return [
		item for item in data
		if (store_name_lower in (item.get("seller_name") or "").lower()
			or store_name_lower in (item.get("seller_type") or "").lower())
		and category_name_lower in (item.get("category") or "").lower()
	]




def main() -> None:
	args = build_parser().parse_args()
	session = create_session()

	if args.discover_categories:
		data = discover_categories(session)
	else:
		# Handle simplified syntax: --store and --cat
		if args.store:
			# Try to use cached grouped data
			import os
			cache_file = "grouped_output2.json"
			
			# Check if cache exists
			if not os.path.exists(cache_file):
				print(f"Məlumat kesintisi yaradılır... (ilk dəfə)")
				# Build cache
				url = urljoin(BASE_URL, "/elanlar")
				items = scrape_category(session, url, pages=3, store_only=False)
				detailed: list[dict[str, Any]] = []
				for item in items:
					try:
						d = scrape_detail(session, item.url)
						detailed.append(asdict(d))
					except Exception:
						detailed.append(asdict(item))
				grouped_data = group_by_store(detailed)
				with open(cache_file, 'w', encoding='utf-8') as f:
					f.write(to_json(grouped_data))
				print(f"✓ {cache_file} yaradıldı")
			
			# Now use cache
			with open(cache_file, 'r', encoding='utf-8') as f:
				grouped = json.load(f)
				all_products = []
				for store in grouped.get('magazalar', []):
					all_products.extend(store['mehsullar'])
			
			# Filter by store and optionally by category
			if args.cat:
				filtered = filter_by_store_and_category(all_products, args.store, args.cat)
				if not filtered:
					print(f"Heç bir məhsul tapılmadı. Mağaza: '{args.store}', Kateqoriya: '{args.cat}'")
			else:
				filtered = filter_by_store(all_products, args.store)
				if not filtered:
					print(f"Heç bir məhsul tapılmadı. Mağaza: '{args.store}'")
			
			data = filtered
		else:
			# Original flow for --url or --category
			url = args.url or args.category
			if not url:
				raise SystemExit("URL verilmədi. --url və ya --category istifadə et.")
			if not url.startswith("http"):
				url = urljoin(BASE_URL, url)

			if args.detail or is_detail_url(url):
				data = asdict(scrape_detail(session, url))
			else:
				items = scrape_category(session, url, pages=args.pages, store_only=args.store_only)
				# Category output now always includes detail-page fields.
				detailed: list[dict[str, Any]] = []
				for item in items:
					try:
						d = scrape_detail(session, item.url)
						detailed.append(asdict(d))
					except Exception:
						# fallback to summary if detail fetch fails
						detailed.append(asdict(item))
				
				# Apply filters if requested
				if args.filter_store:
					if args.filter_category:
						filtered = filter_by_store_and_category(detailed, args.filter_store, args.filter_category)
					else:
						filtered = filter_by_store(detailed, args.filter_store)
					
					if not filtered:
						print(f"Heç bir məhsul tapılmadı. Mağaza: '{args.filter_store}'", end="")
						if args.filter_category:
							print(f", Kateqoriya: '{args.filter_category}'")
						else:
							print()
					data = filtered
				# Group by store if requested
				elif args.group_by_store:
					data = group_by_store(detailed)
				else:
					data = detailed

	if args.output and args.output.lower().endswith(".csv"):
		write_csv(data, args.output)
	elif args.csv:
		csv_path = args.output or "tap_output.csv"
		write_csv(data, csv_path)
	elif args.output:
		with open(args.output, "w", encoding="utf-8") as file:
			file.write(to_json(data))

	output = to_json(data) if args.json or (not args.output and not args.csv) else ""
	if output:
		print(output)


if __name__ == "__main__":
	main()

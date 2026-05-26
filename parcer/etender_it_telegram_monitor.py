import argparse
import json
import os
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - fallback for environments without rapidfuzz
    fuzz = None


API_URL = "https://etender.gov.az/api/events"
DETAIL_URL_TEMPLATE = "https://etender.gov.az/main/competition/detail/{event_id}"

IT_KEYWORDS = [
    "kompüter",
    "komputer",
    "proqram",
    "proqram təminatı",
    "it",
    "informasiya",
    "telekommunikasiya",
    "server",
    "şəbəkə",
    "sebeke",
    "data",
    "kiber",
    "software",
    "hardware",
    "lisenziya",
    "license",
    "texniki dəstək",
    "printer",
    "noutbuk",
    "notebook",
    "surətçıxaran aparat",
    "şəbəkə avadanlığı",
    "rabitə avadanlığı",
    "ups",
    "proyektor",
    "monitor",
    "planşet",
    "texniki avadanlıq",
    "ehtiyat hissələri",
    "kartric",
    "toner tozu",
    "proqram təminatı (software)",
    "proqram təminatı",
    "lisenziya",
    "antivirus",
    "əməliyyat sistemi",
    "ofis proqramı",
    "1C",
    "ERP sistemi",
    "CRM sistemi",
    "verilənlər bazası",
    "proqram platforması",
    "tətbiqi proqram",
    "proqram hazırlanması",
    "it xidmətlər",
    "saytın hazırlanması",
    "mobil tətbiq",
    "veb proqramlaşdırma",
    "informasiya sistemi",
    "elektron xidmətlər portalı",
    "texniki dəstək",
    "xidmətin dəstəklənməsi",
    "texniki xidmət",
    "inteqrasiya",
    "avtomatlaşdırma",
    "rəqəmsallaşdırma",
    "elektron hökumət",
    "məlumat mübadiləsi sistemi",
    "seo xidməti",
    "kibertəhlükəsizlik",
    "informasiya təhlükəsizliyi",
    "firewall",
    "şifrələmə",
    "monitoring sistemi",
    "infrastruktur / bulud",
    "bulud texnologiyaları",
    "data mərkəzi",
    "şəbəkə infrastrukturu",
    "hosting xidməti",
    "domenin qeydiyyatı",
    "internet xətti",
    "strukturlaşdırılmış kabel sistemi",
    "IP kamera sistemi",
    "video nəzarət",
    "giriş nəzarəti",
    "analitika / məlumat",
    "menecment informasiya sistemi",
    "böyük verilənlər",
    "süni intellekt",
    "elektron sənəd dövriyyəsi",
    "arxiv sistemi",
    "məlumat bazasının idarəsi"

]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: str) -> str:
    return " ".join(fold_text(value or "").split())


def fold_text(value: str) -> str:
    """Normalize text and remove Azerbaijani/Unicode accents for matching."""
    text = value.lower()
    translation_table = str.maketrans(
        {
            "ə": "e",
            "ö": "o",
            "ü": "u",
            "ğ": "g",
            "ş": "s",
            "ç": "c",
            "ı": "i",
            "İ": "i",
        }
    )
    text = text.translate(translation_table)
    text = unicodedata.normalize("NFKD", text)
    return "".join(character for character in text if not unicodedata.combining(character))


def fuzzy_keyword_match(haystack: str, keywords: list[str], threshold: int = 85) -> bool:
    """Return True when a keyword is present or close enough to a keyword in the text."""
    if not haystack:
        return False

    haystack_folded = fold_text(haystack)

    if any(fold_text(keyword) in haystack_folded for keyword in keywords):
        return True

    if fuzz is None:
        return False

    for keyword in keywords:
        keyword_folded = fold_text(keyword)
        if fuzz.partial_ratio(haystack_folded, keyword_folded) >= threshold:
            return True
        if fuzz.token_set_ratio(haystack_folded, keyword_folded) >= threshold:
            return True
    return False


def is_it_tender(event: dict[str, Any]) -> bool:
    haystack = normalize_text(
        f"{event.get('eventName', '')} {event.get('buyerOrganizationName', '')}"
    )
    return fuzzy_keyword_match(haystack, IT_KEYWORDS)


def get_requests_session() -> requests.Session:
    """Create a requests Session configured with retries/backoff."""
    session = requests.Session()
    # For VPS/deployment: increase retries and backoff for reliability
    retries = Retry(
        total=4,
        connect=4,
        read=4,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_page(page_number: int, page_size: int = 15, event_status: int = 1) -> dict[str, Any]:
    params = {
        "EventType": 2,
        "PageSize": page_size,
        "PageNumber": page_number,
        "EventStatus": event_status,
        "Keyword": "",
        "buyerOrganizationName": "",
        "documentNumber": "",
        "publishDateFrom": "",
        "publishDateTo": "",
        "AwardedparticipantName": "",
        "AwardedparticipantVoen": "",
        "DocumentViewType": "",
        "IsArchived": "false",
    }

    # Use a session with retries to tolerate transient network errors
    session = get_requests_session()
    # For VPS: allow a longer timeout to tolerate slow network responses
    response = session.get(API_URL, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_recent_events(max_pages: int) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        try:
            payload = fetch_page(page)
        except requests.RequestException as exc:
            print(f"Şəbəkə xətası page={page}: {exc}. Davam etmir, toplanan nəticə qaytarılır.")
            break
        except Exception as exc:
            print(f"Naməlum xəta page={page}: {exc}. Davam etmir.")
            break

        page_items = payload.get("items", [])
        if not page_items:
            break
        events.extend(page_items)
        if not payload.get("hasNextPage", False):
            break
    return events


def load_state(state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return {"last_seen_event_id": 0, "last_check": None}

    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"last_seen_event_id": 0, "last_check": None}
        if "last_seen_event_id" not in data:
            seen_ids = data.get("seen_event_ids", [])
            if isinstance(seen_ids, list) and seen_ids:
                numeric_ids = [int(x) for x in seen_ids if str(x).isdigit()]
                data["last_seen_event_id"] = max(numeric_ids) if numeric_ids else 0
            else:
                data["last_seen_event_id"] = 0
        if not isinstance(data.get("last_seen_event_id"), int):
            try:
                data["last_seen_event_id"] = int(data["last_seen_event_id"])
            except (TypeError, ValueError):
                data["last_seen_event_id"] = 0
        return data
    except json.JSONDecodeError:
        return {"last_seen_event_id": 0, "last_check": None}


def save_state(state_path: Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def format_event_message(event: dict[str, Any]) -> str:
    event_id = event.get("eventId")
    detail_url = DETAIL_URL_TEMPLATE.format(event_id=event_id)
    name = event.get("eventName", "-")
    buyer = event.get("buyerOrganizationName", "-")
    publish_date = event.get("publishDate", "-")
    end_date = event.get("endDate", "-")

    return (
        "🆕 <b>Yeni IT tender</b>\n"
        f"<b>Ad:</b> {name}\n"
        f"<b>Qurum:</b> {buyer}\n"
        f"<b>Yayın:</b> {publish_date}\n"
        f"<b>Bitmə:</b> {end_date}\n"
        f"<b>Link:</b> {detail_url}"
    )


def send_telegram_message(bot_token: str, chat_id: str, message: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    session = get_requests_session()
    # For VPS: give Telegram API a bit more time to respond
    response = session.post(url, json=payload, timeout=12)
    response.raise_for_status()


def process_once(
    *,
    state_path: Path,
    max_pages: int,
    dry_run: bool,
    notify_existing: bool,
    bot_token: str | None,
    chat_ids: list[str] | None,
) -> int:
    state = load_state(state_path)
    last_seen_event_id = int(state.get("last_seen_event_id") or 0)

    all_events = fetch_recent_events(max_pages=max_pages)
    it_events = [event for event in all_events if is_it_tender(event)]

    current_ids = [int(event.get("eventId")) for event in it_events if event.get("eventId") is not None]
    newest_cursor = max(current_ids) if current_ids else last_seen_event_id
    new_events = [
        event
        for event in it_events
        if event.get("eventId") is not None and int(event["eventId"]) > last_seen_event_id
    ]
    new_events.sort(key=lambda event: int(event.get("eventId", 0)), reverse=True)

    is_first_run = last_seen_event_id == 0
    if is_first_run and not notify_existing:
        print(f"İlk işə salınma: {len(current_ids)} IT tender yaddaşa yazıldı, Telegram-a mesaj göndərilmədi.")
        state["last_seen_event_id"] = newest_cursor
        state["last_check"] = now_utc_iso()
        save_state(state_path, state)
        return 0

    if not new_events:
        print("Yeni IT tender yoxdur.")
    else:
        print(f"{len(new_events)} yeni IT tender tapıldı.")

    if not dry_run and (not bot_token or not chat_ids):
        print("XƏTA: TELEGRAM_BOT_TOKEN və ən azı bir TELEGRAM_CHAT_ID tələb olunur.")
        return 2

    for event in new_events:
        msg = format_event_message(event)
        if dry_run:
            print("-" * 80)
            print(msg)
        else:
            for cid in chat_ids or []:
                try:
                    send_telegram_message(bot_token=bot_token or "", chat_id=cid, message=msg)
                    print(f"Göndərildi: {event.get('eventId')} -> {event.get('eventName', '')} (chat_id={cid})")
                except requests.RequestException as exc:
                    print(f"Telegram göndəriş xətası (eventId={event.get('eventId')}, chat_id={cid}): {exc}")

    state["last_seen_event_id"] = newest_cursor
    state["last_check"] = now_utc_iso()
    save_state(state_path, state)
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="eTender IT tender monitoru: yeni tenderləri Telegram-a göndərir."
    )
    parser.add_argument(
        "--state-file",
        default="parcer/.etender_it_state.json",
        help="State fayl yolu (default: parcer/.etender_it_state.json)",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=3,
        help="Yoxlanacaq səhifə sayı (default: 3)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Davamlı rejimdə yoxlama intervalı (saniyə) (default: 300)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Yalnız bir dəfə yoxla və çıx",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Telegram-a göndərmədən yalnız konsola çap et",
    )
    parser.add_argument(
        "--notify-existing",
        action="store_true",
        help="İlk işə salınmada mövcud uyğun tenderləri də bildiriş et",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    state_path = Path(args.state_file)
    max_pages = max(args.pages, 1)

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    # Support multiple chat IDs via TELEGRAM_CHAT_IDS (comma-separated) or single TELEGRAM_CHAT_ID
    chat_ids_env = os.getenv("TELEGRAM_CHAT_IDS") or os.getenv("TELEGRAM_CHAT_ID")
    chat_ids = [c.strip() for c in (chat_ids_env or "").split(",") if c.strip()]

    if args.once:
        return process_once(
            state_path=state_path,
            max_pages=max_pages,
            dry_run=args.dry_run,
            notify_existing=args.notify_existing,
            bot_token=bot_token,
            chat_ids=chat_ids,
        )

    print(f"Monitor başladı. Interval: {args.interval}s | Pages: {max_pages}")
    while True:
        try:
            process_once(
                state_path=state_path,
                max_pages=max_pages,
                dry_run=args.dry_run,
                notify_existing=args.notify_existing,
                bot_token=bot_token,
                chat_ids=chat_ids,
            )
        except requests.RequestException as exc:
            print(f"Şəbəkə xətası: {exc}")
        except Exception as exc:
            print(f"Gözlənilməz xəta: {exc}")

        time.sleep(max(args.interval, 10))


if __name__ == "__main__":
    sys.exit(main())

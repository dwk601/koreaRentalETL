"""Shared Korean text parsing helpers."""

import hashlib
import re
from datetime import datetime, timedelta, timezone


def compute_content_hash(html: str) -> str:
    """Compute SHA256 hash of HTML content."""
    return hashlib.sha256(html.encode()).hexdigest()[:16]


def extract_text(element) -> str:
    """Extract and clean text from an element."""
    if not element:
        return ""
    text = element.get_text(strip=True) if hasattr(element, "get_text") else str(element)
    return " ".join(text.split())


def parse_korean_date(date_str: str) -> str | None:
    """Parse Korean date strings to ISO-8601 UTC.

    Handles: 2024년 5월 1일, 오늘, 어제, 방금 전, ~까지
    """
    if not date_str:
        return None

    date_str = date_str.strip()
    now_utc = datetime.now(timezone.utc)

    # Handle relative dates
    if "오늘" in date_str or "today" in date_str.lower():
        return now_utc.date().isoformat()
    if "어제" in date_str or "yesterday" in date_str.lower():
        return (now_utc - timedelta(days=1)).date().isoformat()
    if "방금" in date_str or "just now" in date_str.lower():
        return now_utc.isoformat()

    # Parse Korean date format: 2024년 5월 1일
    match = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", date_str)
    if match:
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        try:
            return datetime(year, month, day, tzinfo=timezone.utc).isoformat()
        except ValueError:
            return None

    return None


def parse_korean_price(price_str: str) -> dict:
    """Parse Korean price strings.

    Returns: {raw_price_ko, rent_monthly_usd, deposit_usd, lease_type, currency_raw}
    """
    if not price_str:
        return {
            "raw_price_ko": None,
            "rent_monthly_usd": None,
            "deposit_usd": None,
            "lease_type": None,
            "currency_raw": None,
        }

    price_str = price_str.strip()
    result = {
        "raw_price_ko": price_str,
        "rent_monthly_usd": None,
        "deposit_usd": None,
        "lease_type": None,
        "currency_raw": None,
    }

    # Detect lease type
    if "월세" in price_str:
        result["lease_type"] = "monthly_rent"
    elif "보증금" in price_str:
        result["lease_type"] = "deposit"
    elif "전세" in price_str:
        result["lease_type"] = "jeonse"
    elif "단기" in price_str or "short" in price_str.lower():
        result["lease_type"] = "short_term"
    elif "리스" in price_str or "lease" in price_str.lower():
        result["lease_type"] = "lease"

    # Extract numbers (KRW or USD)
    numbers = re.findall(r"[\d,]+", price_str)
    if numbers:
        num = int(numbers[0].replace(",", ""))
        if "$" in price_str or "USD" in price_str.upper():
            result["rent_monthly_usd"] = num
            result["currency_raw"] = "USD"
        else:
            # Assume KRW; rough conversion (1 USD ≈ 1200 KRW)
            result["rent_monthly_usd"] = num // 1200 if num > 10000 else num
            result["currency_raw"] = "KRW"

    return result


def extract_contact_block(element) -> str:
    """Extract contact info block (phone, email, kakao)."""
    if not element:
        return ""
    return extract_text(element)

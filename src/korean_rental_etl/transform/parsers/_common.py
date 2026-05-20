"""Shared Korean text parsing helpers."""

import re
from datetime import UTC, datetime, timedelta

from korean_rental_etl.extract.raw_writer import compute_content_hash  # noqa: F401
from korean_rental_etl.text_utils import extract_title_bracket, first_body_line  # noqa: F401

__all__ = [
    "compute_content_hash",
    "extract_text",
    "extract_labelled_field",
    "extract_body_text",
    "extract_contact_block",
    "extract_title_bracket",
    "first_body_line",
    "infer_location",
]


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
    now_utc = datetime.now(UTC)

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
            return datetime(year, month, day, tzinfo=UTC).isoformat()
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


def extract_labelled_field(text: str, labels: list[str]) -> str:
    """Extract value after a labelled line in Korean body text.

    Scans line-by-line and returns the value after any of the given labels.
    Supports both ASCII colon ':' and full-width colon '：'.

    Args:
        text: Body text to search.
        labels: List of label strings to match (e.g., ['위치', 'Location']).

    Returns:
        The value after the label, or empty string if not found.
    """
    if not text or not labels:
        return ""

    for line in text.split("\n"):
        line = line.strip()
        for label in labels:
            # Match both ASCII ':' and full-width '：'
            for sep in [":", "："]:
                prefix = f"{label}{sep}"
                if line.startswith(prefix):
                    return line[len(prefix) :].strip()
    return ""


def extract_body_text(soup: object, selectors: list[str]) -> str:
    """Extract clean text from the first matching CSS selector.

    Preserves line breaks from <p> and <br> tags.

    Args:
        soup: BeautifulSoup object.
        selectors: List of CSS selectors to try in order.

    Returns:
        Clean whitespace-collapsed text with line breaks, or empty string if no match.
    """
    if not soup or not selectors:
        return ""

    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            # Extract text preserving paragraph breaks
            lines = []
            for child in element.descendants:
                if isinstance(child, str):
                    text = child.strip()
                    if text:
                        lines.append(text)
                elif hasattr(child, "name") and child.name in ("p", "br", "div"):
                    # Check if this is a direct child (not nested)
                    if child.parent == element or (
                        hasattr(child.parent, "name") and child.parent.name in ("p", "div")
                    ):
                        pass  # Will be handled by text extraction
            # Simpler approach: get text from each <p> tag separately
            paragraphs = []
            for p in element.find_all(["p", "div"], recursive=False):
                text = extract_text(p)
                if text:
                    paragraphs.append(text)
            if paragraphs:
                return "\n".join(paragraphs)
            # Fallback to full text if no paragraphs
            return extract_text(element)
    return ""


def infer_location(title: str, body: str, labelled: str = "") -> str:
    """Best-effort location string from labelled, title bracket, or body first line.

    Priority:
      1. Explicit '위치:' / 'Location:' value if present.
      2. '[bracket]' tag in title joined with first body line for richer context.
      3. First body line on its own.
      4. Title bracket on its own.

    Args:
        title: Listing title (e.g. 'title_ko').
        body: Listing body (e.g. 'body_ko').
        labelled: Pre-extracted labelled value (from extract_labelled_field), if any.

    Returns:
        A non-empty location string when any signal is available, else ''.
    """
    if labelled:
        return labelled
    bracket = extract_title_bracket(title)
    head = first_body_line(body)
    # If bracket already appears in head, head alone is richer; otherwise combine.
    if bracket and head and bracket not in head:
        return f"{bracket} {head}".strip()
    return head or bracket

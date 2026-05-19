"""Location normalizer - extracts city, state, country from raw location text."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# City mappings
US_CITIES = {
    "la",
    "los angeles",
    "애틀랜타",
    "atlanta",
    "oc",
    "orange county",
    "sf",
    "san francisco",
    "샌프란시스코",
    "sd",
    "san diego",
    "샌디에고",
    "ny",
    "new york",
    "뉴욕",
    "nj",
    "new jersey",
    "뉴저지",
    "queens",
    "퀸즈",
    "flushing",
    "플러싱",
    "irvine",
    "어바인",
    "duluth",
    "둘루스",
    "sunny",
    "sunnyvale",
    "새너니",
    "fullerton",
    "풀러턴",
    "hollywood",
    "할리우드",
    "burbank",
    "버뱅크",
    "koreatown",
    "코리아타운",
    "ktown",
}

KR_CITIES = {
    "서울",
    "부산",
    "인천",
    "대구",
    "대전",
    "광주",
    "울산",
    "세종",
    "경기",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
}

STATES = {
    "ca": "CA",
    "california": "CA",
    "캘리포니아": "CA",
    "ga": "GA",
    "georgia": "GA",
    "조지아": "GA",
    "ny": "NY",
    "new york": "NY",
    "nj": "NJ",
    "new jersey": "NJ",
    "tx": "TX",
    "texas": "TX",
    "wa": "WA",
    "washington": "WA",
    "il": "IL",
    "illinois": "IL",
}


def normalize_location(raw_location: str) -> dict[str, Any]:
    """Normalize raw location into city, state, country.

    Returns:
        Dict with city, state_or_province, country, address_raw.
    """
    if not raw_location:
        return {
            "city": None,
            "state_or_province": None,
            "country": None,
            "address_raw": raw_location,
        }

    city: str | None = None
    state: str | None = None
    country = "US"  # Default assumption for Korean community boards

    text = raw_location.lower()

    # Detect state
    for key, value in STATES.items():
        if key in text:
            state = value
            break

    # Detect city
    for c in US_CITIES:
        if c.lower() in text:
            city = c.title()
            break

    # Detect Korean cities
    if not city:
        for c in KR_CITIES:
            if c in raw_location:
                city = c
                country = "KR"
                state = None
                break

    # If no city found, use the raw text truncated
    if not city:
        city = raw_location[:50] if len(raw_location) <= 50 else raw_location[:50] + "..."

    return {
        "city": city,
        "state_or_province": state,
        "country": country,
        "address_raw": raw_location,
    }

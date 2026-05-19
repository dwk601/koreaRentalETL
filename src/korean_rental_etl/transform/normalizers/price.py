"""Price normalizer - converts Korean raw price strings to structured USD."""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)

# Exchange rate (approximate, should be configurable)
KRW_TO_USD = Decimal("0.00075")


def normalize_price(raw_price: str) -> dict[str, Any]:
    """Normalize Korean price string into structured fields.

    Handles patterns like:
        - 월세: $1,500 / 월세 $1,500
        - 전세: $30,000
        - 보증금: $3,000
        - 단기: $2,000/month
        - 리스: $500
        - ₩1,000,000 (KRW)

    Returns:
        Dict with rent_monthly_usd, deposit_usd, lease_type, currency_raw, price_raw_ko
    """
    if not raw_price:
        return {
            "rent_monthly_usd": None,
            "deposit_usd": None,
            "lease_type": None,
            "currency_raw": None,
            "price_raw_ko": raw_price,
        }

    rent_monthly: Decimal | None = None
    deposit: Decimal | None = None
    lease_type: str | None = None
    currency_raw = "USD"

    # Detect lease type from keywords
    lower_text = raw_price.lower()
    if "전세" in raw_price:
        lease_type = "jeonse"
    elif "단기" in raw_price or "서브렛" in raw_price or "sublet" in lower_text:
        lease_type = "short_term"
    elif "리스" in raw_price or "lease" in lower_text:
        lease_type = "lease"
    elif "월세" in raw_price or "/month" in lower_text or "monthly" in lower_text:
        lease_type = "monthly"
    elif "보증금" in raw_price:
        lease_type = "monthly"  # Common pattern: deposit + monthly
    else:
        lease_type = "monthly"  # Default assumption

    # Extract all numbers with currency
    # Pattern: $1,500 or ₩1,000,000 or 1,500원
    usd_matches = re.findall(r"[$]\s*([\d,]+)", raw_price)
    krw_matches = re.findall(r"[₩]\s*([\d,]+)", raw_price)
    won_matches = re.findall(r"([\d,]+)\s*원", raw_price)

    all_usd = [v for m in usd_matches if (v := _parse_amount(m)) is not None]
    all_krw = [v for m in (krw_matches + won_matches) if (v := _parse_amount(m)) is not None]

    if all_krw and not all_usd:
        # All amounts in KRW
        currency_raw = "KRW"
        all_usd = [k * KRW_TO_USD for k in all_krw]

    # Assign amounts: largest = deposit, rest = monthly
    if len(all_usd) >= 2:
        # Usually deposit is larger or equal
        deposit = max(all_usd)
        rent_monthly = min(all_usd)
    elif len(all_usd) == 1:
        single = all_usd[0]
        if lease_type == "jeonse":
            deposit = single
        else:
            rent_monthly = single

    return {
        "rent_monthly_usd": rent_monthly,
        "deposit_usd": deposit,
        "lease_type": lease_type,
        "currency_raw": currency_raw,
        "price_raw_ko": raw_price,
    }


def _parse_amount(text: str) -> Decimal | None:
    """Parse a numeric amount string to Decimal."""
    try:
        cleaned = text.replace(",", "").replace(" ", "")
        return Decimal(cleaned)
    except Exception:
        return None

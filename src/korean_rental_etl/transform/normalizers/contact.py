"""Contact normalizer - extracts phone, kakao_id, email from contact text."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def normalize_contact(contact_block: str) -> dict[str, Any]:
    """Extract structured contact info from raw contact text.

    Returns:
        Dict with phone, kakao_id, email.
    """
    if not contact_block:
        return {"phone": None, "kakao_id": None, "email": None}

    phone = extract_phone(contact_block)
    kakao_id = extract_kakao(contact_block)
    email = extract_email(contact_block)

    return {
        "phone": phone,
        "kakao_id": kakao_id,
        "email": email,
    }


def extract_phone(text: str) -> str | None:
    """Extract US/Korean phone numbers from text."""
    patterns = [
        r"(\d{3}-\d{3}-\d{4})",  # 213-555-1234
        r"(\(\d{3}\)\s*\d{3}-\d{4})",  # (213) 555-1234
        r"(\d{3}\.\d{3}\.\d{4})",  # 213.555.1234
        r"(\d{10,11})",  # 01012345678
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def extract_kakao(text: str) -> str | None:
    """Extract KakaoTalk ID from text."""
    patterns = [
        r"(?:카카오|kakao)[:\s]*([a-zA-Z0-9_\-]+)",
        r"(?:카톡|katok)[:\s]*([a-zA-Z0-9_\-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def extract_email(text: str) -> str | None:
    """Extract email address from text."""
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    match = re.search(pattern, text)
    if match:
        return match.group()
    return None

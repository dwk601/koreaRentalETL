"""Date normalizer - converts Korean date strings to ISO-8601 UTC."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def normalize_date(raw_date: str) -> dict[str, Any]:
    """Normalize Korean date string into posted_at_utc.

    Handles patterns like:
        - 2024년 5월 1일
        - 오늘, 어제, 방금 전
        - 05-01, 2024-05-01
        - ~까지 (deadline, skip)

    Returns:
        Dict with posted_at_utc or None.
    """
    if not raw_date:
        return {"posted_at_utc": None}

    raw_date = raw_date.strip()

    # Handle relative dates
    now = datetime.now(UTC)
    if raw_date in ("오늘", "today"):
        return {"posted_at_utc": now}
    if raw_date in ("어제", "yesterday"):
        return {"posted_at_utc": now - timedelta(days=1)}
    if "방금" in raw_date or "just now" in raw_date.lower():
        return {"posted_at_utc": now}

    # Handle Korean format: 2024년 5월 1일
    match = re.match(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", raw_date)
    if match:
        year, month, day = map(int, match.groups())
        try:
            return {"posted_at_utc": datetime(year, month, day, tzinfo=UTC)}
        except ValueError:
            logger.warning("Invalid Korean date: %s", raw_date)
            return {"posted_at_utc": None}

    # Handle ISO format: 2024-05-01
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw_date)
    if match:
        year, month, day = map(int, match.groups())
        try:
            return {"posted_at_utc": datetime(year, month, day, tzinfo=UTC)}
        except ValueError:
            return {"posted_at_utc": None}

    # Handle short format: 05-01 (assume current year)
    match = re.match(r"(\d{2})-(\d{2})", raw_date)
    if match:
        month, day = map(int, match.groups())
        try:
            return {"posted_at_utc": datetime(now.year, month, day, tzinfo=UTC)}
        except ValueError:
            return {"posted_at_utc": None}

    # Handle MM/DD/YYYY
    match = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw_date)
    if match:
        month, day, year = map(int, match.groups())
        try:
            return {"posted_at_utc": datetime(year, month, day, tzinfo=UTC)}
        except ValueError:
            return {"posted_at_utc": None}

    return {"posted_at_utc": None}

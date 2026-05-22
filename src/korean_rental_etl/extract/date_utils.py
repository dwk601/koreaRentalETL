"""Korean date parsing utilities for rental listings."""

from __future__ import annotations

import re
from datetime import date, timedelta


def parse_korean_date(s: str, today: date | None = None) -> date | None:
    """Parse Korean date strings in various formats.

    Handles:
    - YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD
    - MM-DD, MM/DD, MM.DD (infers year as most recent past occurrence)
    - M월D일 (Korean format)
    - Relative: N분전, N시간전, N일전, 어제, 오늘, 방금전

    Args:
        s: Date string to parse.
        today: Reference date for relative parsing. Defaults to today.

    Returns:
        Parsed date or None if unparseable.
    """
    if not s or not isinstance(s, str):
        return None

    s = s.strip()
    if today is None:
        today = date.today()

    # Try YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD
    # Allow optional whitespace around separators (e.g. "2026. 05. 20")
    for sep in ["-", ".", "/"]:
        match = re.match(
            r"(\d{4})\s*" + re.escape(sep) + r"\s*(\d{1,2})\s*" + re.escape(sep) + r"\s*(\d{1,2})",
            s,
        )
        if match:
            try:
                return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            except ValueError:
                pass

    # Try MM-DD-YY, MM/DD/YY, MM.DD.YY
    for sep in ["-", ".", "/"]:
        match = re.match(
            r"(\d{1,2})\s*"
            + re.escape(sep)
            + r"\s*(\d{1,2})\s*"
            + re.escape(sep)
            + r"\s*(\d{2})(?:\s|$)",
            s,
        )
        if match:
            try:
                month, day = int(match.group(1)), int(match.group(2))
                year = 2000 + int(match.group(3))
                return date(year, month, day)
            except ValueError:
                pass

    # Try MM-DD, MM/DD, MM.DD (infer year)
    # Allow optional whitespace after the separator (e.g. "05. 20" — common on
    # Korean community boards like svkoreans).
    for sep in ["-", ".", "/"]:
        match = re.match(r"(\d{1,2})\s*" + re.escape(sep) + r"\s*(\d{1,2})(?:\s|$)", s)
        if match:
            try:
                month, day = int(match.group(1)), int(match.group(2))
                # Find most recent past occurrence of this month/day
                candidate = date(today.year, month, day)
                if candidate > today:
                    candidate = date(today.year - 1, month, day)
                return candidate
            except ValueError:
                pass

    # Try M월D일 (Korean format)
    match = re.match(r"(\d{1,2})월(\d{1,2})일", s)
    if match:
        try:
            month, day = int(match.group(1)), int(match.group(2))
            candidate = date(today.year, month, day)
            if candidate > today:
                candidate = date(today.year - 1, month, day)
            return candidate
        except ValueError:
            pass

    # Try HH:MM or HH:MM:SS (time-only, assume today)
    match = re.match(r"(\d{1,2}):(\d{2})(?::(\d{2}))?$", s)
    if match:
        return today

    # Try relative formats
    if "방금전" in s or "방금" in s:
        return today

    if "오늘" in s:
        return today

    if "어제" in s:
        return today - timedelta(days=1)

    # N분전 (minutes ago)
    match = re.search(r"(\d+)분전", s)
    if match:
        return today

    # N시간전 (hours ago)
    match = re.search(r"(\d+)시간전", s)
    if match:
        return today

    # N일전 (days ago)
    match = re.search(r"(\d+)일전", s)
    if match:
        days_ago = int(match.group(1))
        return today - timedelta(days=days_ago)

    return None

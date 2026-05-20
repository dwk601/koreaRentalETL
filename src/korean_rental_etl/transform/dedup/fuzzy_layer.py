"""Cross-source fuzzy dedup using RapidFuzz with time-window blocking."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.90
TIME_WINDOW_DAYS = 7


def find_duplicates(listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find duplicate listings within a batch using time-window blocking.

    Args:
        listings: List of listing dicts with title_ko, city, posted_at_utc, rent_monthly_usd, etc.

    Returns:
        List of listings marked with is_duplicate and canonical_id.
    """
    if not listings:
        return []

    # Group by city
    by_city: dict[str, list[dict[str, Any]]] = {}
    for listing in listings:
        city = (listing.get("city") or "").lower()
        by_city.setdefault(city, []).append(listing)

    results: list[dict[str, Any]] = []
    processed = set()

    for _city, city_listings in by_city.items():
        if len(city_listings) < 2:
            for listing in city_listings:
                listing["is_duplicate"] = False
                listing["canonical_id"] = None
                results.append(listing)
            continue

        # Compare all pairs within time window
        for i, listing_a in enumerate(city_listings):
            if i in processed:
                continue

            group = [listing_a]
            text_a = f"{listing_a.get('title_ko', '')} {listing_a.get('rent_monthly_usd', '')}"
            posted_a = listing_a.get("posted_at_utc")

            for j, listing_b in enumerate(city_listings):
                if i == j or j in processed:
                    continue

                posted_b = listing_b.get("posted_at_utc")

                # Check time window: ±7 days
                if posted_a and posted_b:
                    try:
                        date_a = (
                            posted_a.date()
                            if isinstance(posted_a, datetime)
                            else datetime.fromisoformat(str(posted_a).replace("Z", "+00:00")).date()
                        )
                        date_b = (
                            posted_b.date()
                            if isinstance(posted_b, datetime)
                            else datetime.fromisoformat(str(posted_b).replace("Z", "+00:00")).date()
                        )
                        days_diff = abs((date_a - date_b).days)
                        if days_diff > TIME_WINDOW_DAYS:
                            continue
                    except (ValueError, AttributeError, TypeError):
                        pass

                text_b = f"{listing_b.get('title_ko', '')} {listing_b.get('rent_monthly_usd', '')}"
                if not text_a.strip() or not text_b.strip():
                    continue

                score = fuzz.token_set_ratio(text_a, text_b) / 100.0
                if score >= SIMILARITY_THRESHOLD:
                    group.append(listing_b)
                    processed.add(j)

            if len(group) > 1:
                # Pick canonical: earliest posted_at (handle datetime, string, or None)
                def _sort_key(x: dict[str, Any]) -> str:
                    p = x.get("posted_at_utc")
                    if p is None:
                        return "9999"
                    if isinstance(p, datetime):
                        return p.isoformat()
                    return str(p)

                canonical = min(group, key=_sort_key)
                canonical_id = canonical.get("id", 0)

                for member in group:
                    member["is_duplicate"] = member is not canonical
                    member["canonical_id"] = canonical_id if member is not canonical else None
                    results.append(member)
                processed.add(i)
            else:
                listing_a["is_duplicate"] = False
                listing_a["canonical_id"] = None
                results.append(listing_a)
                processed.add(i)

    return results

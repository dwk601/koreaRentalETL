"""Cleanup operations for stale listings and old raw pages."""

from __future__ import annotations

import logging

from korean_rental_etl.db.connection import get_cursor

logger = logging.getLogger(__name__)


def mark_stale_listings_inactive(days: int = 14) -> int:
    """Mark listings as inactive if not seen in N days.

    Args:
        days: Number of days (default 14).

    Returns:
        Number of rows updated.
    """
    with get_cursor() as cur:
        cur.execute(
            """
            UPDATE public.listings
            SET is_active = false, updated_at = NOW()
            WHERE is_active = true AND last_seen_at < NOW() - INTERVAL '%s days'
            """,
            (days,),
        )
        count = cur.rowcount

    logger.info("Marked %d listings as inactive (not seen in %d days)", count, days)
    return count


def purge_old_raw_pages(days: int = 90) -> int:
    """Delete raw HTML pages older than N days.

    Args:
        days: Number of days (default 90).

    Returns:
        Number of rows deleted.
    """
    with get_cursor() as cur:
        cur.execute(
            """
            DELETE FROM raw.scraped_pages
            WHERE fetched_at < NOW() - INTERVAL '%s days'
            """,
            (days,),
        )
        count = cur.rowcount

    logger.info("Purged %d raw pages (older than %d days)", count, days)
    return count

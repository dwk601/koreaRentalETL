"""Raw HTML writer - persists fetched HTML idempotently."""

from __future__ import annotations

import hashlib
import logging

from korean_rental_etl.db.connection import get_cursor

logger = logging.getLogger(__name__)


def compute_content_hash(html: str) -> str:
    """Compute SHA-256 hash of HTML content.

    Args:
        html: Raw HTML string.

    Returns:
        Hex digest of SHA-256 hash.
    """
    return hashlib.sha256(html.encode("utf-8")).hexdigest()


def save(
    source_id: int,
    url: str,
    html: str,
    http_status: int | None = None,
) -> bool:
    """Save raw HTML to raw.scraped_pages.

    Uses ON CONFLICT (source_id, url, content_hash) DO NOTHING for idempotency.

    Args:
        source_id: ID of the source from public.sources.
        url: URL that was fetched.
        html: Raw HTML content.
        http_status: HTTP status code of the response.

    Returns:
        True if a new row was inserted, False if it already existed (duplicate).
    """
    content_hash = compute_content_hash(html)

    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO raw.scraped_pages (source_id, url, html_content, content_hash, http_status)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (source_id, url, content_hash) DO NOTHING
            RETURNING id
            """,
            (source_id, url, html, content_hash, http_status),
        )
        result = cur.fetchone()
        inserted = result is not None

    if inserted:
        logger.debug(
            "Saved new page: source_id=%d url=%s hash=%s", source_id, url, content_hash[:12]
        )
    else:
        logger.debug(
            "Page already exists: source_id=%d url=%s hash=%s", source_id, url, content_hash[:12]
        )

    return inserted


def get_page(source_id: int, url: str) -> dict[str, object] | None:
    """Get the most recent scraped page for a source+URL.

    Args:
        source_id: Source ID.
        url: URL to look up.

    Returns:
        Dict with page data or None if not found.
    """
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, source_id, url, html_content, content_hash, http_status, fetched_at
            FROM raw.scraped_pages
            WHERE source_id = %s AND url = %s
            ORDER BY fetched_at DESC
            LIMIT 1
            """,
            (source_id, url),
        )
        return cur.fetchone()  # type: ignore[return-value]


def get_unparsed_pages(source_id: int, limit: int = 100) -> list[dict[str, object]]:
    """Get raw pages that haven't been parsed yet.

    A page is considered unparsed if its content_hash doesn't appear
    in staging.listings_staging for the same source.

    Args:
        source_id: Source ID to filter by.
        limit: Maximum number of pages to return.

    Returns:
        List of dicts with page data.
    """
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT rp.id, rp.source_id, rp.url, rp.html_content, rp.content_hash
            FROM raw.scraped_pages rp
            WHERE rp.source_id = %s
              AND NOT EXISTS (
                  SELECT 1 FROM staging.listings_staging ls
                  WHERE ls.source_id = rp.source_id
                    AND ls.content_hash = rp.content_hash
              )
            ORDER BY rp.fetched_at DESC
            LIMIT %s
            """,
            (source_id, limit),
        )
        return cur.fetchall()  # type: ignore[return-value]

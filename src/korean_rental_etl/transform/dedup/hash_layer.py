"""Content-hash dedup layer — skip rows with duplicate content."""

import logging

from korean_rental_etl.db.connection import get_cursor

logger = logging.getLogger(__name__)


def should_skip_by_hash(source_id: int, content_hash: str) -> bool:
    """Check if content_hash already exists for this source.

    Args:
        source_id: Source ID.
        content_hash: Content hash.

    Returns:
        True if hash exists (skip), False if new (process).
    """
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id FROM staging.listings_staging
            WHERE source_id = %s AND content_hash = %s
            LIMIT 1
            """,
            (source_id, content_hash),
        )
        result = cur.fetchone()
    return result is not None

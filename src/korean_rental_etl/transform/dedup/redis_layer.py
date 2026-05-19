"""Redis URL cache - dedup layer 1.

Short-circuits re-fetches by tracking seen URLs per source in Redis SETs.
TTL: 14 days (matches stale window).
"""

from __future__ import annotations

import logging
import os

import redis

logger = logging.getLogger(__name__)

DEFAULT_TTL_SEC = 14 * 24 * 60 * 60  # 14 days

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """Get or create the global Redis client.

    Returns:
        Redis client instance.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", "6379")),
            db=int(os.environ.get("REDIS_DB", "0")),
            password=os.environ.get("REDIS_PASSWORD") or None,
            decode_responses=True,
        )
    return _redis_client


def close_redis() -> None:
    """Close the global Redis client."""
    global _redis_client
    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None


def _key(source_name: str) -> str:
    """Build Redis key for a source's URL set."""
    return f"seen_urls:{source_name}"


def seen(source_name: str, url: str) -> bool:
    """Check if a URL has been seen for a source.

    Args:
        source_name: Name of the source.
        url: URL to check.

    Returns:
        True if URL was previously seen.
    """
    client = get_redis_client()
    return bool(client.sismember(_key(source_name), url))


def mark(source_name: str, url: str, ttl_sec: int = DEFAULT_TTL_SEC) -> None:
    """Mark a URL as seen for a source.

    Args:
        source_name: Name of the source.
        url: URL to mark.
        ttl_sec: TTL in seconds for the set (refreshed on each mark).
    """
    client = get_redis_client()
    key = _key(source_name)
    client.sadd(key, url)
    client.expire(key, ttl_sec)
    logger.debug("Marked URL seen: source=%s url=%s", source_name, url)


def mark_batch(source_name: str, urls: list[str], ttl_sec: int = DEFAULT_TTL_SEC) -> int:
    """Mark multiple URLs as seen for a source.

    Args:
        source_name: Name of the source.
        urls: List of URLs to mark.
        ttl_sec: TTL in seconds for the set.

    Returns:
        Number of newly added URLs.
    """
    if not urls:
        return 0
    client = get_redis_client()
    key = _key(source_name)
    added: int = client.sadd(key, *urls)  # type: ignore[assignment]
    client.expire(key, ttl_sec)
    logger.debug("Batch marked %d new URLs for source=%s", added, source_name)
    return added


def count(source_name: str) -> int:
    """Count seen URLs for a source.

    Args:
        source_name: Name of the source.

    Returns:
        Number of URLs in the set.
    """
    client = get_redis_client()
    return int(client.scard(_key(source_name)))  # type: ignore[arg-type]


def clear(source_name: str) -> None:
    """Clear all seen URLs for a source.

    Args:
        source_name: Name of the source.
    """
    client = get_redis_client()
    client.delete(_key(source_name))
    logger.info("Cleared seen URLs for source=%s", source_name)


def test_connection() -> bool:
    """Test Redis connectivity.

    Returns:
        True if connection succeeds.
    """
    try:
        client = get_redis_client()
        return bool(client.ping())
    except Exception:
        return False

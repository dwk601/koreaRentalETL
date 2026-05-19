"""Nominatim geocoder with Redis caching and rate limiting."""

from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import Any

import httpx

from korean_rental_etl.transform.dedup.redis_layer import get_redis_client

logger = logging.getLogger(__name__)

DEFAULT_RATE_LIMIT_SEC = 1.0
DEFAULT_CACHE_TTL_SEC = 30 * 24 * 60 * 60  # 30 days
_last_request_time: float = 0.0


def _cache_key(address: str) -> str:
    return f"geocode:{hashlib.sha256(address.encode()).hexdigest()[:16]}"


def _rate_limit() -> None:
    """Enforce global rate limit between requests."""
    global _last_request_time
    min_interval = float(os.environ.get("NOMINATIM_RATE_LIMIT_PER_SEC", "1.0"))
    elapsed = time.time() - _last_request_time
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _last_request_time = time.time()


def geocode(address_raw: str, city: str | None = None, country: str = "US") -> dict[str, Any]:
    """Geocode an address using Nominatim with Redis caching.

    Args:
        address_raw: Raw address string.
        city: City name.
        country: Country code.

    Returns:
        Dict with lat, lon, or None if failed.
    """
    if not address_raw:
        return {"lat": None, "lon": None}

    # Build query string
    query = f"{address_raw}, {city or ''}, {country}".strip(", ")

    # Check cache
    client = get_redis_client()
    cache_key = _cache_key(query)
    cached: str | None = client.get(cache_key)  # type: ignore[assignment]
    if cached:
        logger.debug("Geocode cache hit for: %s", query[:50])
        lat, lon = cached.split(",")
        return {"lat": float(lat), "lon": float(lon)}

    # Rate limit
    _rate_limit()

    # Call Nominatim
    user_agent = os.environ.get("NOMINATIM_USER_AGENT", "korean-rental-etl/0.1.0")
    try:
        response = httpx.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": user_agent},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.warning("Geocoding failed for '%s': %s", query[:50], e)
        return {"lat": None, "lon": None}

    if not data:
        logger.debug("No geocode results for: %s", query[:50])
        return {"lat": None, "lon": None}

    lat_f = float(data[0]["lat"])
    lon_f = float(data[0]["lon"])

    # Cache result
    client.setex(cache_key, DEFAULT_CACHE_TTL_SEC, f"{lat_f},{lon_f}")
    logger.debug("Geocoded: %s -> lat=%.4f lon=%.4f", query[:50], lat_f, lon_f)

    return {"lat": lat_f, "lon": lon_f}

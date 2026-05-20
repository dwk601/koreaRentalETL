"""Staging writer - inserts transformed rows into staging.listings_staging."""

from __future__ import annotations

import logging

from psycopg.types.json import Json

from korean_rental_etl.db.connection import get_cursor

logger = logging.getLogger(__name__)


def insert_staging_row(row: dict) -> int | None:
    """Insert a transformed row into staging.listings_staging.

    Uses ON CONFLICT to handle re-parses of the same (source_id, source_listing_id).

    Args:
        row: Dict with keys: source_id, source_listing_id, url, content_hash,
             title_ko, body_ko, raw_price, raw_location, raw_posted_at, contact_block,
             rent_monthly_usd, deposit_usd, lease_type, currency_raw, price_raw_ko,
             posted_at_utc, city, state_or_province, country, address_raw,
             phone, kakao_id, email, category, lat, lon, is_duplicate, duplicate_of,
             canonical_id, errors.

    Returns:
        The new/updated row id, or None if already present.
    """
    with get_cursor() as cur:
        # Build geo_point from lat/lon if both present
        lat = row.get("lat")
        lon = row.get("lon")

        cur.execute(
            """
            INSERT INTO staging.listings_staging (
                source_id, source_listing_id, url, content_hash,
                title_ko, body_ko, raw_price, raw_location, raw_posted_at, contact_block,
                rent_monthly_usd, deposit_usd, lease_type, currency_raw, price_raw_ko,
                posted_at_utc, city, state_or_province, country, address_raw,
                phone, kakao_id, email, category, geo_point,
                is_duplicate, duplicate_of, canonical_id, errors
            )
            VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                CASE WHEN %s::float8 IS NOT NULL AND %s::float8 IS NOT NULL
                     THEN ST_SetSRID(ST_MakePoint(%s::float8, %s::float8), 4326)
                     ELSE NULL END,
                %s, %s, %s, %s
            )
            ON CONFLICT (source_id, source_listing_id) DO UPDATE SET
                parsed_at = NOW(),
                content_hash = EXCLUDED.content_hash,
                title_ko = EXCLUDED.title_ko,
                body_ko = EXCLUDED.body_ko,
                raw_price = EXCLUDED.raw_price,
                raw_location = EXCLUDED.raw_location,
                raw_posted_at = EXCLUDED.raw_posted_at,
                contact_block = EXCLUDED.contact_block,
                rent_monthly_usd = EXCLUDED.rent_monthly_usd,
                deposit_usd = EXCLUDED.deposit_usd,
                lease_type = EXCLUDED.lease_type,
                currency_raw = EXCLUDED.currency_raw,
                price_raw_ko = EXCLUDED.price_raw_ko,
                posted_at_utc = EXCLUDED.posted_at_utc,
                city = EXCLUDED.city,
                state_or_province = EXCLUDED.state_or_province,
                country = EXCLUDED.country,
                address_raw = EXCLUDED.address_raw,
                phone = EXCLUDED.phone,
                kakao_id = EXCLUDED.kakao_id,
                email = EXCLUDED.email,
                category = EXCLUDED.category,
                geo_point = EXCLUDED.geo_point,
                is_duplicate = EXCLUDED.is_duplicate,
                duplicate_of = EXCLUDED.duplicate_of,
                canonical_id = EXCLUDED.canonical_id,
                errors = EXCLUDED.errors
            RETURNING id
            """,
            (
                row.get("source_id"),
                row.get("source_listing_id"),
                row.get("url"),
                row.get("content_hash"),
                row.get("title_ko"),
                row.get("body_ko"),
                row.get("raw_price"),
                row.get("raw_location"),
                row.get("raw_posted_at"),
                row.get("contact_block"),
                row.get("rent_monthly_usd"),
                row.get("deposit_usd"),
                row.get("lease_type"),
                row.get("currency_raw"),
                row.get("price_raw_ko"),
                row.get("posted_at_utc"),
                row.get("city"),
                row.get("state_or_province"),
                row.get("country"),
                row.get("address_raw"),
                row.get("phone"),
                row.get("kakao_id"),
                row.get("email"),
                row.get("category"),
                lon,
                lat,
                lon,
                lat,
                row.get("is_duplicate", False),
                row.get("duplicate_of"),
                row.get("canonical_id"),
                Json(row.get("errors") or {}),
            ),
        )
        result = cur.fetchone()
        row_id = result["id"] if result else None

    if row_id:
        logger.debug(
            "Inserted staging row: id=%d source_id=%d source_listing_id=%s",
            row_id,
            row.get("source_id"),
            row.get("source_listing_id"),
        )
    return row_id


def get_recent_unloaded(source_id: int | None = None, days: int = 7) -> list[dict]:
    """Get recent unloaded staging rows for fuzzy dedup.

    Args:
        source_id: Optional source ID to filter by. If None, returns all sources.
        days: Number of days to look back (default 7).

    Returns:
        List of dicts with id, source_id, source_listing_id, title_ko, rent_monthly_usd,
        city, posted_at_utc.
    """
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, source_id, source_listing_id, title_ko, rent_monthly_usd, city, posted_at_utc
            FROM staging.listings_staging
            WHERE loaded_at IS NULL
              AND parsed_at >= NOW() - (%s || ' days')::interval
              AND (%s::int IS NULL OR source_id = %s::int)
            ORDER BY parsed_at DESC
            """,
            (days, source_id, source_id),
        )
        return cur.fetchall()  # type: ignore[return-value]

"""Integration tests for staging_writer."""

import pytest

from korean_rental_etl.db.connection import get_cursor
from korean_rental_etl.transform.staging_writer import get_recent_unloaded, insert_staging_row


@pytest.mark.integration
class TestStagingWriter:
    """Integration tests for staging_writer against test Postgres."""

    def test_insert_staging_row_with_geo_point(self):
        """Insert a row with lat/lon and verify geo_point is set."""
        row = {
            "source_id": 1,
            "source_listing_id": "test_12345",
            "url": "https://example.com/test",
            "content_hash": "a" * 64,
            "title_ko": "테스트 제목",
            "body_ko": "테스트 본문",
            "raw_price": "$1,500",
            "raw_location": "LA",
            "raw_posted_at": "2024-05-01",
            "contact_block": "213-555-1234",
            "rent_monthly_usd": 1500.00,
            "deposit_usd": 3000.00,
            "lease_type": "monthly",
            "currency_raw": "USD",
            "price_raw_ko": "$1,500",
            "posted_at_utc": "2024-05-01T00:00:00Z",
            "city": "Los Angeles",
            "state_or_province": "CA",
            "country": "US",
            "address_raw": "123 Main St, LA",
            "phone": "213-555-1234",
            "kakao_id": None,
            "email": None,
            "category": "apartment",
            "lat": 34.05,
            "lon": -118.25,
            "is_duplicate": False,
            "duplicate_of": None,
            "canonical_id": None,
            "errors": {},
        }

        row_id = insert_staging_row(row)
        assert row_id is not None

        # Verify the row was inserted with geo_point
        with get_cursor() as cur:
            cur.execute(
                """
                SELECT ST_X(geo_point) as lon, ST_Y(geo_point) as lat
                FROM staging.listings_staging
                WHERE id = %s
                """,
                (row_id,),
            )
            result = cur.fetchone()
            assert result is not None
            assert abs(result["lon"] - (-118.25)) < 1e-6
            assert abs(result["lat"] - 34.05) < 1e-6

    def test_insert_staging_row_without_geo_point(self):
        """Insert a row without lat/lon and verify geo_point is NULL."""
        row = {
            "source_id": 1,
            "source_listing_id": "test_67890",
            "url": "https://example.com/test2",
            "content_hash": "b" * 64,
            "title_ko": "테스트 제목 2",
            "body_ko": "테스트 본문 2",
            "raw_price": "$2,000",
            "raw_location": "OC",
            "raw_posted_at": "2024-05-02",
            "contact_block": "949-555-5678",
            "rent_monthly_usd": 2000.00,
            "deposit_usd": 2000.00,
            "lease_type": "monthly",
            "currency_raw": "USD",
            "price_raw_ko": "$2,000",
            "posted_at_utc": "2024-05-02T00:00:00Z",
            "city": "Orange County",
            "state_or_province": "CA",
            "country": "US",
            "address_raw": "456 Oak Ave, OC",
            "phone": "949-555-5678",
            "kakao_id": None,
            "email": None,
            "category": "condo",
            "lat": None,
            "lon": None,
            "is_duplicate": False,
            "duplicate_of": None,
            "canonical_id": None,
            "errors": {},
        }

        row_id = insert_staging_row(row)
        assert row_id is not None

        # Verify geo_point is NULL
        with get_cursor() as cur:
            cur.execute(
                """
                SELECT geo_point IS NULL as is_null
                FROM staging.listings_staging
                WHERE id = %s
                """,
                (row_id,),
            )
            result = cur.fetchone()
            assert result is not None
            assert result["is_null"] is True

    def test_insert_staging_row_upsert_on_conflict(self):
        """Insert a row, then insert again with same (source_id, source_listing_id) and verify UPDATE."""
        row1 = {
            "source_id": 1,
            "source_listing_id": "test_upsert",
            "url": "https://example.com/upsert",
            "content_hash": "c" * 64,
            "title_ko": "원래 제목",
            "body_ko": "원래 본문",
            "raw_price": "$1,000",
            "raw_location": "LA",
            "raw_posted_at": "2024-05-01",
            "contact_block": "213-555-1111",
            "rent_monthly_usd": 1000.00,
            "deposit_usd": 1000.00,
            "lease_type": "monthly",
            "currency_raw": "USD",
            "price_raw_ko": "$1,000",
            "posted_at_utc": "2024-05-01T00:00:00Z",
            "city": "Los Angeles",
            "state_or_province": "CA",
            "country": "US",
            "address_raw": "111 First St",
            "phone": "213-555-1111",
            "kakao_id": None,
            "email": None,
            "category": "apartment",
            "lat": 34.05,
            "lon": -118.25,
            "is_duplicate": False,
            "duplicate_of": None,
            "canonical_id": None,
            "errors": {},
        }

        row_id_1 = insert_staging_row(row1)
        assert row_id_1 is not None

        # Insert again with updated rent_monthly_usd
        row2 = row1.copy()
        row2["rent_monthly_usd"] = 1500.00
        row2["content_hash"] = "d" * 64

        row_id_2 = insert_staging_row(row2)
        assert row_id_2 == row_id_1  # Same row ID

        # Verify the row was updated
        with get_cursor() as cur:
            cur.execute(
                """
                SELECT rent_monthly_usd, content_hash
                FROM staging.listings_staging
                WHERE id = %s
                """,
                (row_id_1,),
            )
            result = cur.fetchone()
            assert result is not None
            assert result["rent_monthly_usd"] == 1500.00
            assert result["content_hash"] == "d" * 64

    def test_get_recent_unloaded_all_sources(self):
        """Get recent unloaded rows across all sources."""
        # Insert a test row
        row = {
            "source_id": 1,
            "source_listing_id": "test_recent_1",
            "url": "https://example.com/recent1",
            "content_hash": "e" * 64,
            "title_ko": "최근 제목",
            "body_ko": "최근 본문",
            "raw_price": "$1,200",
            "raw_location": "LA",
            "raw_posted_at": "2024-05-01",
            "contact_block": "213-555-2222",
            "rent_monthly_usd": 1200.00,
            "deposit_usd": 1200.00,
            "lease_type": "monthly",
            "currency_raw": "USD",
            "price_raw_ko": "$1,200",
            "posted_at_utc": "2024-05-01T00:00:00Z",
            "city": "Los Angeles",
            "state_or_province": "CA",
            "country": "US",
            "address_raw": "222 Second St",
            "phone": "213-555-2222",
            "kakao_id": None,
            "email": None,
            "category": "apartment",
            "lat": 34.05,
            "lon": -118.25,
            "is_duplicate": False,
            "duplicate_of": None,
            "canonical_id": None,
            "errors": {},
        }

        insert_staging_row(row)

        # Get recent unloaded rows
        recent = get_recent_unloaded(source_id=None, days=7)
        assert len(recent) > 0
        # Find our test row
        test_row = next((r for r in recent if r["source_listing_id"] == "test_recent_1"), None)
        assert test_row is not None
        assert test_row["title_ko"] == "최근 제목"
        assert test_row["rent_monthly_usd"] == 1200.00

    def test_get_recent_unloaded_single_source(self):
        """Get recent unloaded rows for a specific source."""
        # Insert test rows for different sources
        for source_id in [1, 2]:
            row = {
                "source_id": source_id,
                "source_listing_id": f"test_source_{source_id}",
                "url": f"https://example.com/source{source_id}",
                "content_hash": f"{'f' * 63}{source_id}",
                "title_ko": f"소스 {source_id} 제목",
                "body_ko": f"소스 {source_id} 본문",
                "raw_price": "$1,300",
                "raw_location": "LA",
                "raw_posted_at": "2024-05-01",
                "contact_block": "213-555-3333",
                "rent_monthly_usd": 1300.00,
                "deposit_usd": 1300.00,
                "lease_type": "monthly",
                "currency_raw": "USD",
                "price_raw_ko": "$1,300",
                "posted_at_utc": "2024-05-01T00:00:00Z",
                "city": "Los Angeles",
                "state_or_province": "CA",
                "country": "US",
                "address_raw": "333 Third St",
                "phone": "213-555-3333",
                "kakao_id": None,
                "email": None,
                "category": "apartment",
                "lat": 34.05,
                "lon": -118.25,
                "is_duplicate": False,
                "duplicate_of": None,
                "canonical_id": None,
                "errors": {},
            }
            insert_staging_row(row)

        # Get recent unloaded rows for source 1 only
        recent = get_recent_unloaded(source_id=1, days=7)
        # All returned rows should be from source 1
        for row in recent:
            assert row["source_id"] == 1

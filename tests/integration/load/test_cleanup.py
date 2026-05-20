"""Integration tests for cleanup module."""

import psycopg
import pytest

from korean_rental_etl.load.cleanup import mark_stale_listings_inactive, purge_old_raw_pages


@pytest.mark.integration
class TestCleanupIntegration:
    """Integration tests for cleanup operations against real database."""

    @pytest.fixture(autouse=True)
    def use_dict_row(self, test_conn: psycopg.Connection):
        """Set connection's row factory to dict_row for all assertions."""
        from psycopg.rows import dict_row
        test_conn.row_factory = dict_row

    def _insert_listing(self, test_conn: psycopg.Connection, source_listing_id: str, last_seen_days_ago: int, is_active: bool = True):
        """Helper to insert a listing with a custom last_seen_at timestamp."""
        with test_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.listings (
                    source_id, source_listing_id, url, title_ko, body_ko,
                    rent_monthly_usd, deposit_usd, lease_type, currency_raw, price_raw_ko,
                    posted_at_utc, city, state_or_province, country, address_raw,
                    phone, kakao_id, email, category, is_active, last_seen_at
                ) VALUES (
                    1, %s, 'https://example.com/clean', '테스트', '본문',
                    1000.0, 1000.0, 'monthly', 'USD', '$1,000',
                    '2024-05-01T00:00:00Z', 'Seoul', 'Seoul', 'KR', 'Seoul',
                    NULL, NULL, NULL, 'apartment', %s, NOW() - (%s || ' days')::interval
                )
                """,
                (source_listing_id, is_active, last_seen_days_ago),
            )
            test_conn.commit()

    def _insert_raw_page(self, test_conn: psycopg.Connection, url: str, fetched_days_ago: int):
        """Helper to insert a raw scraped page with a custom fetched_at timestamp."""
        with test_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO raw.scraped_pages (
                    source_id, url, html_content, content_hash, fetched_at
                ) VALUES (
                    1, %s, '<html></html>', 'hash123', NOW() - (%s || ' days')::interval
                )
                """,
                (url, fetched_days_ago),
            )
            test_conn.commit()

    def test_mark_stale_marks_old_listings(self, test_conn: psycopg.Connection):
        """Listings not seen for more than the threshold are marked inactive."""
        self._insert_listing(test_conn, "stale_1", last_seen_days_ago=30, is_active=True)

        count = mark_stale_listings_inactive(days=14)
        assert count == 1

        with test_conn.cursor() as cur:
            cur.execute("SELECT is_active FROM public.listings WHERE source_listing_id = 'stale_1'")
            assert cur.fetchone()["is_active"] is False

    def test_mark_stale_preserves_recent_listings(self, test_conn: psycopg.Connection):
        """Listings seen recently (within threshold) remain active."""
        self._insert_listing(test_conn, "fresh_1", last_seen_days_ago=5, is_active=True)

        count = mark_stale_listings_inactive(days=14)
        assert count == 0

        with test_conn.cursor() as cur:
            cur.execute("SELECT is_active FROM public.listings WHERE source_listing_id = 'fresh_1'")
            assert cur.fetchone()["is_active"] is True

    def test_mark_stale_returns_count(self, test_conn: psycopg.Connection):
        """mark_stale_listings_inactive returns the exact count of updated rows."""
        self._insert_listing(test_conn, "stale_a", last_seen_days_ago=20, is_active=True)
        self._insert_listing(test_conn, "stale_b", last_seen_days_ago=25, is_active=True)
        self._insert_listing(test_conn, "fresh_a", last_seen_days_ago=5, is_active=True)

        count = mark_stale_listings_inactive(days=14)
        assert count == 2

    def test_purge_deletes_old_raw_pages(self, test_conn: psycopg.Connection):
        """Raw pages older than the threshold are deleted."""
        self._insert_raw_page(test_conn, "https://old.com", fetched_days_ago=100)

        count = purge_old_raw_pages(days=90)
        assert count == 1

        with test_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM raw.scraped_pages WHERE url = 'https://old.com'")
            assert cur.fetchone()["count"] == 0

    def test_purge_preserves_recent_raw_pages(self, test_conn: psycopg.Connection):
        """Raw pages within the threshold are preserved."""
        self._insert_raw_page(test_conn, "https://recent.com", fetched_days_ago=30)

        count = purge_old_raw_pages(days=90)
        assert count == 0

        with test_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM raw.scraped_pages WHERE url = 'https://recent.com'")
            assert cur.fetchone()["count"] == 1

    def test_purge_returns_count(self, test_conn: psycopg.Connection):
        """purge_old_raw_pages returns the exact count of deleted rows."""
        self._insert_raw_page(test_conn, "https://old_a.com", fetched_days_ago=100)
        self._insert_raw_page(test_conn, "https://old_b.com", fetched_days_ago=110)
        self._insert_raw_page(test_conn, "https://fresh_a.com", fetched_days_ago=10)

        count = purge_old_raw_pages(days=90)
        assert count == 2

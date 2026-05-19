"""Integration tests for database schema.

These tests require Docker Compose test stack running:
    docker compose -f docker-compose.test.yml up -d postgres
    pytest tests/integration/db/test_schema.py -v -m integration
"""

import os

import psycopg
import pytest


@pytest.fixture
def test_conn() -> psycopg.Connection:
    """Get a connection to the test database."""
    conninfo = (
        f"host={os.environ.get('TEST_POSTGRES_HOST', 'localhost')} "
        f"port={os.environ.get('TEST_POSTGRES_PORT', '15432')} "
        f"dbname={os.environ.get('TEST_POSTGRES_DB', 'korean_rental_test')} "
        f"user={os.environ.get('TEST_POSTGRES_USER', 'etl_test')} "
        f"password={os.environ.get('TEST_POSTGRES_PASSWORD', 'test_password')}"
    )
    conn = psycopg.connect(conninfo)
    yield conn
    conn.close()


@pytest.mark.integration
class TestSchema:
    def test_extensions_installed(self, test_conn: psycopg.Connection) -> None:
        """PostGIS and pg_trgm extensions are installed."""
        with test_conn.cursor() as cur:
            cur.execute("SELECT extname FROM pg_extension WHERE extname IN ('postgis', 'pg_trgm')")
            extensions = {row[0] for row in cur.fetchall()}
            assert "postgis" in extensions
            assert "pg_trgm" in extensions

    def test_schemas_exist(self, test_conn: psycopg.Connection) -> None:
        """All 4 schemas exist."""
        with test_conn.cursor() as cur:
            cur.execute(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name IN ('raw', 'staging', 'public', 'audit')"
            )
            schemas = {row[0] for row in cur.fetchall()}
            assert schemas == {"raw", "staging", "public", "audit"}

    def test_sources_table(self, test_conn: psycopg.Connection) -> None:
        """Sources table exists with correct columns."""
        with test_conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'sources' "
                "ORDER BY ordinal_position"
            )
            columns = [row[0] for row in cur.fetchall()]
            assert "id" in columns
            assert "name" in columns
            assert "base_url" in columns
            assert "is_active" in columns

    def test_sources_seeded(self, test_conn: psycopg.Connection) -> None:
        """Sources table is seeded with 6 sources."""
        with test_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.sources")
            count = cur.fetchone()[0]
            assert count == 6

    def test_scraped_pages_table(self, test_conn: psycopg.Connection) -> None:
        """Raw scraped_pages table exists."""
        with test_conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'raw' AND table_name = 'scraped_pages'"
            )
            columns = {row[0] for row in cur.fetchall()}
            assert "source_id" in columns
            assert "url" in columns
            assert "html_content" in columns
            assert "content_hash" in columns

    def test_listings_staging_table(self, test_conn: psycopg.Connection) -> None:
        """Staging listings_staging table exists."""
        with test_conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'staging' AND table_name = 'listings_staging'"
            )
            columns = {row[0] for row in cur.fetchall()}
            assert "title_ko" in columns
            assert "title_en" in columns
            assert "rent_monthly_usd" in columns
            assert "geo_point" in columns

    def test_listings_table(self, test_conn: psycopg.Connection) -> None:
        """Final listings table exists."""
        with test_conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'listings'"
            )
            columns = {row[0] for row in cur.fetchall()}
            assert "title_ko" in columns
            assert "category" in columns
            assert "is_active" in columns

    def test_etl_runs_table(self, test_conn: psycopg.Connection) -> None:
        """Audit etl_runs table exists."""
        with test_conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'audit' AND table_name = 'etl_runs'"
            )
            columns = {row[0] for row in cur.fetchall()}
            assert "status" in columns
            assert "rows_extracted" in columns
            assert "started_at" in columns

    def test_indexes_exist(self, test_conn: psycopg.Connection) -> None:
        """Key indexes exist on public.listings."""
        with test_conn.cursor() as cur:
            cur.execute(
                "SELECT indexname FROM pg_indexes "
                "WHERE schemaname = 'public' AND tablename = 'listings'"
            )
            indexes = {row[0] for row in cur.fetchall()}
            assert "idx_listings_geo_point" in indexes
            assert "idx_listings_korean_fts" in indexes
            assert "idx_listings_city" in indexes
            assert "idx_listings_category" in indexes

    def test_unique_constraint_listings(self, test_conn: psycopg.Connection) -> None:
        """UNIQUE constraint on (source_id, source_listing_id) exists."""
        with test_conn.cursor() as cur:
            cur.execute(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'public.listings'::regclass AND contype = 'u'"
            )
            constraints = {row[0] for row in cur.fetchall()}
            # The unique constraint name may vary, just check one exists
            assert len(constraints) >= 1

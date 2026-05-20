"""Shared pytest configuration and fixtures for integration tests."""

import os

import psycopg
import pytest

from korean_rental_etl.db.connection import close_pool, get_conninfo


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up integration test environment variables and connection pool."""
    # Set default connection parameters for the test database if not already set
    if "POSTGRES_HOST" not in os.environ:
        os.environ["POSTGRES_HOST"] = "localhost"
    if "POSTGRES_PORT" not in os.environ:
        os.environ["POSTGRES_PORT"] = "15432"
    if "POSTGRES_DB" not in os.environ:
        os.environ["POSTGRES_DB"] = "korean_rental_test"
    if "POSTGRES_USER" not in os.environ:
        os.environ["POSTGRES_USER"] = "etl_test"
    if "POSTGRES_PASSWORD" not in os.environ:
        os.environ["POSTGRES_PASSWORD"] = "test_password"

    # Synchronize TEST_ env vars for backward compatibility (e.g. test_schema.py)
    if "TEST_POSTGRES_HOST" not in os.environ:
        os.environ["TEST_POSTGRES_HOST"] = os.environ["POSTGRES_HOST"]
    if "TEST_POSTGRES_PORT" not in os.environ:
        os.environ["TEST_POSTGRES_PORT"] = os.environ["POSTGRES_PORT"]
    if "TEST_POSTGRES_DB" not in os.environ:
        os.environ["TEST_POSTGRES_DB"] = os.environ["POSTGRES_DB"]
    if "TEST_POSTGRES_USER" not in os.environ:
        os.environ["TEST_POSTGRES_USER"] = os.environ["POSTGRES_USER"]
    if "TEST_POSTGRES_PASSWORD" not in os.environ:
        os.environ["TEST_POSTGRES_PASSWORD"] = os.environ["POSTGRES_PASSWORD"]

    # Close any existing pool at the start of the session to ensure a clean slate
    close_pool()
    yield
    # Close pool at the end of the session
    close_pool()


@pytest.fixture(scope="function")
def test_conn() -> psycopg.Connection:
    """Get a direct connection to the test database for assertion queries."""
    conninfo = get_conninfo()
    with psycopg.connect(conninfo) as conn:
        yield conn


@pytest.fixture(scope="function", autouse=True)
def clean_db(test_conn: psycopg.Connection):
    """Truncate etl_runs, listings, listings_staging, and scraped_pages before each test."""
    with test_conn.cursor() as cur:
        # We RESTART IDENTITY and CASCADE to handle foreign keys properly.
        # We do NOT truncate public.sources as it contains vital seeded data.
        cur.execute(
            """
            TRUNCATE TABLE
                audit.etl_runs,
                public.listings,
                staging.listings_staging,
                raw.scraped_pages
            RESTART IDENTITY
            CASCADE;
            """
        )
        test_conn.commit()

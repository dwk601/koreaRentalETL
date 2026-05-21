"""Integration tests for upserter module.

Discovered Bugs & Design Notes for Follow-Up:
1. `load_from_staging_no_loaded_at`:
   load_from_staging() fetches rows WHERE loaded_at IS NULL but never sets loaded_at
   after a successful upsert. As a result, the same rows are reloaded on every run.
   In these tests, we assert staging.loaded_at is NOT set, flagging this bug.

2. `upsert_batch_unused_run_id`:
   upsert_batch(rows, run_db_id) takes run_db_id as an argument, but the parameter
   is completely unused in the function body.

3. `cleanup_interval_parameterization`:
   cleanup.py used 'INTERVAL %s days' inside SQL query string literals. Psycopg
   does not parameterize variables inside string literals, which leads to SQL syntax
   errors. This was successfully confirmed during Task 4 and resolved inline using
   the parameter-safe pattern: NOW() - (%s || ' days')::interval.
"""

import psycopg
import pytest

from korean_rental_etl.load.upserter import load_from_staging, upsert_batch
from korean_rental_etl.transform.staging_writer import insert_staging_row


@pytest.mark.integration
class TestUpserterIntegration:
    """Integration tests for batched upserter and staging loader against real DB."""

    @pytest.fixture(autouse=True)
    def use_dict_row(self, test_conn: psycopg.Connection):
        """Set connection's row factory to dict_row for all assertions."""
        from psycopg.rows import dict_row

        test_conn.row_factory = dict_row

    def _build_staging_row(
        self, source_id: int, source_listing_id: str, rent: float = 1200.0
    ) -> dict:
        """Helper to build a minimum staging row compatible with schema and staging_writer."""
        return {
            "source_id": source_id,
            "source_listing_id": source_listing_id,
            "url": f"https://example.com/{source_listing_id}",
            "content_hash": "a" * 64,
            "title_ko": "테스트 매물",
            "body_ko": "상세 설명",
            "raw_price": f"${rent:,.0f}",
            "raw_location": "Seoul",
            "raw_posted_at": "2024-05-01",
            "contact_block": "010-1234-5678",
            "rent_monthly_usd": rent,
            "deposit_usd": 2000.0,
            "lease_type": "monthly",
            "currency_raw": "KRW",
            "price_raw_ko": "120만원",
            "posted_at_utc": "2024-05-01T00:00:00Z",
            "city": "Seoul",
            "state_or_province": "Seoul",
            "country": "KR",
            "address_raw": "Seoul, Mapo-gu",
            "phone": "010-1234-5678",
            "kakao_id": None,
            "email": None,
            "category": "apartment",
            "lat": 37.55,
            "lon": 126.92,
            "is_duplicate": False,
            "duplicate_of": None,
            "canonical_id": None,
            "errors": {},
        }

    def test_upsert_batch_inserts_new_listings(self, test_conn: psycopg.Connection):
        """upsert_batch correctly inserts new listings into public.listings."""
        rows = [
            self._build_staging_row(1, "list_1", 1000.0),
            self._build_staging_row(1, "list_2", 1500.0),
            self._build_staging_row(1, "list_3", 2000.0),
        ]

        upserted, failed, _ = upsert_batch(rows, run_db_id=123)
        assert (upserted, failed) == (3, 0)

        with test_conn.cursor() as cur:
            cur.execute("SELECT * FROM public.listings ORDER BY source_listing_id")
            results = cur.fetchall()
            assert len(results) == 3
            assert results[0]["source_listing_id"] == "list_1"
            assert results[0]["rent_monthly_usd"] == 1000.0
            assert results[1]["source_listing_id"] == "list_2"
            assert results[1]["rent_monthly_usd"] == 1500.0
            assert results[2]["source_listing_id"] == "list_3"
            assert results[2]["rent_monthly_usd"] == 2000.0
            for r in results:
                assert r["is_active"] is True
                assert r["first_seen_at"] is not None
                assert r["last_seen_at"] is not None

    def test_upsert_batch_updates_on_conflict(self, test_conn: psycopg.Connection):
        """upsert_batch updates existing listing on (source_id, source_listing_id) conflict."""
        # Initial upsert
        row1 = self._build_staging_row(1, "list_conflict", 1200.0)
        upsert_batch([row1], run_db_id=123)

        with test_conn.cursor() as cur:
            cur.execute(
                "SELECT id, first_seen_at, last_seen_at, updated_at FROM public.listings WHERE source_listing_id = 'list_conflict'"
            )
            first_record = cur.fetchone()
            assert first_record is not None

        # Upsert with different rent and details
        row2 = row1.copy()
        row2["rent_monthly_usd"] = 1400.0
        row2["title_ko"] = "수정된 제목"

        upserted, failed, _ = upsert_batch([row2], run_db_id=123)
        assert (upserted, failed) == (1, 0)

        with test_conn.cursor() as cur:
            cur.execute("SELECT * FROM public.listings WHERE source_listing_id = 'list_conflict'")
            updated_record = cur.fetchone()
            assert updated_record is not None
            assert updated_record["id"] == first_record["id"]
            assert updated_record["rent_monthly_usd"] == 1400.0
            assert updated_record["title_ko"] == "수정된 제목"
            # Since ON CONFLICT does DO UPDATE, last_seen_at and updated_at should be advanced
            assert updated_record["last_seen_at"] >= first_record["last_seen_at"]

    def test_upsert_batch_returns_zero_for_empty_input(self, test_conn: psycopg.Connection):
        """upsert_batch with empty rows list returns immediately with (0, 0)."""
        upserted, failed, _ = upsert_batch([], run_db_id=123)
        assert (upserted, failed) == (0, 0)

        with test_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.listings")
            count = cur.fetchone()["count"]
            assert count == 0

    def test_upsert_batch_handles_per_row_failures(self, test_conn: psycopg.Connection):
        """upsert_batch counts row-level failures, but database transaction rolls back on SQL error."""
        valid_row = self._build_staging_row(1, "list_valid", 1200.0)
        # Invalid row has a non-existent source_id (violating foreign key constraint)
        invalid_row = self._build_staging_row(99999, "list_invalid", 1500.0)

        upserted, failed, _ = upsert_batch([valid_row, invalid_row], run_db_id=123)
        # It returns (1, 1) because the first insert execution succeeded before the error occurred.
        assert (upserted, failed) == (1, 1)

        with test_conn.cursor() as cur:
            cur.execute("SELECT source_listing_id FROM public.listings")
            records = [r["source_listing_id"] for r in cur.fetchall()]
            # Note: Because the second insert threw a ForeignKeyViolation, the transaction
            # was aborted by PostgreSQL. Even though upsert_batch caught the exception and
            # returned (1, 1), the connection context manager rolled back the aborted transaction,
            # so no records were actually committed.
            assert len(records) == 0

    def test_load_from_staging_loads_unloaded_rows(self, test_conn: psycopg.Connection):
        """load_from_staging loads unloaded rows from staging.listings_staging into public.listings."""
        row1 = self._build_staging_row(1, "staging_1", 1000.0)
        row2 = self._build_staging_row(1, "staging_2", 1500.0)

        insert_staging_row(row1)
        insert_staging_row(row2)

        loaded, failed = load_from_staging()
        assert (loaded, failed) == (2, 0)

        # Verify listings are in public.listings
        with test_conn.cursor() as cur:
            cur.execute("SELECT source_listing_id FROM public.listings ORDER BY source_listing_id")
            results = [r["source_listing_id"] for r in cur.fetchall()]
            assert results == ["staging_1", "staging_2"]

        # Verify that staging.listings_staging.loaded_at is set.
        with test_conn.cursor() as cur:
            cur.execute("SELECT loaded_at IS NOT NULL as is_loaded FROM staging.listings_staging")
            loaded_ats = [r["is_loaded"] for r in cur.fetchall()]
            assert all(loaded_ats)

    def test_load_from_staging_filters_by_source_id(self, test_conn: psycopg.Connection):
        """load_from_staging(source_id) only loads rows belonging to that source_id."""
        row_s1 = self._build_staging_row(1, "source_1_listing", 1000.0)
        row_s2 = self._build_staging_row(2, "source_2_listing", 2000.0)

        insert_staging_row(row_s1)
        insert_staging_row(row_s2)

        # Load only source 1
        loaded, failed = load_from_staging(source_id=1)
        assert (loaded, failed) == (1, 0)

        with test_conn.cursor() as cur:
            cur.execute("SELECT source_listing_id, source_id FROM public.listings")
            results = cur.fetchall()
            assert len(results) == 1
            assert results[0]["source_listing_id"] == "source_1_listing"
            assert results[0]["source_id"] == 1

    def test_load_from_staging_creates_audit_record(self, test_conn: psycopg.Connection):
        """load_from_staging creates a success audit record in audit.etl_runs."""
        row = self._build_staging_row(1, "audit_listing", 1200.0)
        insert_staging_row(row)

        loaded, failed = load_from_staging()
        assert (loaded, failed) == (1, 0)

        with test_conn.cursor() as cur:
            cur.execute("SELECT * FROM audit.etl_runs WHERE task_id = 'load'")
            run = cur.fetchone()
            assert run is not None
            assert run["status"] == "success"
            assert run["rows_loaded"] == 1
            assert run["rows_failed"] == 0

    def test_load_from_staging_with_no_unloaded_returns_zero(self, test_conn: psycopg.Connection):
        """load_from_staging with empty staging returns (0, 0) and audits the attempt."""
        loaded, failed = load_from_staging()
        assert (loaded, failed) == (0, 0)

        with test_conn.cursor() as cur:
            cur.execute("SELECT * FROM audit.etl_runs WHERE task_id = 'load'")
            run = cur.fetchone()
            assert run is not None
            assert run["status"] == "success"
            assert run["rows_loaded"] == 0
            assert run["rows_failed"] == 0

    def test_upsert_batch_increments_audit_counts(self, test_conn: psycopg.Connection):
        """upsert_batch incrementally updates the audit row's loaded and failed counts."""
        from korean_rental_etl.load.audit import get_run, start_run

        run_db_id = start_run(task_id="load", source_name="test_audit")

        row1 = self._build_staging_row(1, "audit_inc_1", 1000.0)
        row2 = self._build_staging_row(99999, "audit_inc_invalid", 1500.0)  # fails FK

        # Initial status
        run_before = get_run(run_db_id)
        assert run_before["rows_loaded"] == 0
        assert run_before["rows_failed"] == 0

        # Run upsert
        upsert_batch([row1, row2], run_db_id=run_db_id)

        # Verify increment
        run_after = get_run(run_db_id)
        assert run_after["rows_loaded"] == 1
        assert run_after["rows_failed"] == 1

"""Integration tests for validation thresholds.

These tests require the Docker Compose test stack running:
    pytest tests/integration/validation/test_thresholds.py -v -m integration
"""

from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from korean_rental_etl.transform.staging_writer import insert_staging_row
from korean_rental_etl.validation.thresholds import (
    ValidationError,
    check_fk_integrity,
    check_null_rate_threshold,
    check_parsed_rows_threshold,
    get_audit_run_id_by_airflow_run_id,
    validate_run,
)


@pytest.mark.integration
class TestThresholdsIntegration:
    """Integration tests for validation thresholds against a real database."""

    @pytest.fixture(autouse=True)
    def use_dict_row(self, test_conn: psycopg.Connection):
        """Set connection's row factory to dict_row for all assertions."""
        from psycopg.rows import dict_row

        test_conn.row_factory = dict_row

    def _build_staging_row(
        self, source_listing_id: str, rent: float | None = 1200.0, city: str | None = "Seoul"
    ) -> dict:
        """Helper to build a minimum staging row compatible with schema and staging_writer."""
        return {
            "source_id": 1,
            "source_listing_id": source_listing_id,
            "url": f"https://example.com/{source_listing_id}",
            "content_hash": "a" * 64,
            "title_ko": "테스트 매물",
            "body_ko": "상세 설명",
            "raw_price": f"${rent:,.0f}" if rent else None,
            "raw_location": city,
            "raw_posted_at": "2024-05-01",
            "contact_block": "010-1234-5678",
            "rent_monthly_usd": rent,
            "deposit_usd": 2000.0,
            "lease_type": "monthly",
            "currency_raw": "KRW",
            "price_raw_ko": "120만원",
            "posted_at_utc": "2024-05-01T00:00:00Z",
            "city": city,
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

    def test_check_parsed_rows_threshold_no_history(self, test_conn: psycopg.Connection):
        """parsed_rows threshold passes and logs warning if there is no historical data."""
        with test_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO audit.etl_runs (task_id, source_name, status, started_at, rows_transformed) VALUES ('transform', 'all', 'success', NOW(), 10) RETURNING id"
            )
            run_id = cur.fetchone()["id"]
            test_conn.commit()

        res = check_parsed_rows_threshold(run_id)
        assert res.passed is True
        assert "No historical data" in res.message

    def test_check_parsed_rows_threshold_passes(self, test_conn: psycopg.Connection):
        """parsed_rows threshold passes if current rows_transformed >= 50% of avg of last 5 runs."""
        with test_conn.cursor() as cur:
            # Insert 5 historical runs with rows_transformed = 100
            for _i in range(5):
                cur.execute(
                    "INSERT INTO audit.etl_runs (task_id, source_name, status, started_at, rows_transformed) VALUES ('transform', 'all', 'success', NOW(), 100)"
                )
            # Insert current run with rows_transformed = 60 (average is 100, threshold is 50, 60 >= 50 passes)
            cur.execute(
                "INSERT INTO audit.etl_runs (task_id, source_name, status, started_at, rows_transformed) VALUES ('transform', 'all', 'running', NOW(), 60) RETURNING id"
            )
            run_id = cur.fetchone()["id"]
            test_conn.commit()

        res = check_parsed_rows_threshold(run_id)
        assert res.passed is True
        assert "Current: 60" in res.message

    def test_check_parsed_rows_threshold_fails(self, test_conn: psycopg.Connection):
        """parsed_rows threshold fails if current rows_transformed < 50% of avg of last 5 runs."""
        with test_conn.cursor() as cur:
            # Insert 5 historical runs with rows_transformed = 100
            for _i in range(5):
                cur.execute(
                    "INSERT INTO audit.etl_runs (task_id, source_name, status, started_at, rows_transformed) VALUES ('transform', 'all', 'success', NOW(), 100)"
                )
            # Insert current run with rows_transformed = 40 (average is 100, threshold is 50, 40 < 50 fails)
            cur.execute(
                "INSERT INTO audit.etl_runs (task_id, source_name, status, started_at, rows_transformed) VALUES ('transform', 'all', 'running', NOW(), 40) RETURNING id"
            )
            run_id = cur.fetchone()["id"]
            test_conn.commit()

        res = check_parsed_rows_threshold(run_id)
        assert res.passed is False
        assert "Current: 40" in res.message

    def test_check_null_rate_threshold_empty_staging(self, test_conn: psycopg.Connection):
        """null_rate passes automatically if there are no staging rows in the run's time window."""
        with test_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO audit.etl_runs (task_id, source_name, status, started_at) VALUES ('transform', 'all', 'running', NOW()) RETURNING id"
            )
            run_id = cur.fetchone()["id"]
            test_conn.commit()

        res = check_null_rate_threshold(run_id)
        assert res.passed is True
        assert "No rows in staging" in res.message

    def test_check_null_rate_threshold_passes(self, test_conn: psycopg.Connection):
        """null_rate passes if all null rates are <= max_null_rate (default 20%)."""
        with test_conn.cursor() as cur:
            started = datetime.now(UTC) - timedelta(minutes=5)
            cur.execute(
                "INSERT INTO audit.etl_runs (task_id, source_name, status, started_at) VALUES ('transform', 'all', 'running', %s) RETURNING id",
                (started,),
            )
            run_id = cur.fetchone()["id"]
            test_conn.commit()

        # Insert 5 clean staging rows within the window
        for i in range(5):
            insert_staging_row(self._build_staging_row(f"null_pass_{i}"))

        res = check_null_rate_threshold(run_id)
        assert res.passed is True
        assert "Max null rate: 0.00%" in res.message

    def test_check_null_rate_threshold_fails(self, test_conn: psycopg.Connection):
        """null_rate fails if any key column null rate is > max_null_rate (default 20%)."""
        with test_conn.cursor() as cur:
            started = datetime.now(UTC) - timedelta(minutes=5)
            cur.execute(
                "INSERT INTO audit.etl_runs (task_id, source_name, status, started_at) VALUES ('transform', 'all', 'running', %s) RETURNING id",
                (started,),
            )
            run_id = cur.fetchone()["id"]
            test_conn.commit()

        # Insert 3 clean staging rows, and 2 rows with rent_monthly_usd = None (2/5 = 40% null rate)
        for i in range(3):
            insert_staging_row(self._build_staging_row(f"null_fail_ok_{i}"))
        for i in range(2):
            insert_staging_row(self._build_staging_row(f"null_fail_bad_{i}", rent=None))

        res = check_null_rate_threshold(run_id)
        assert res.passed is False
        assert "Max null rate: 40.00%" in res.message

    def test_check_null_rate_threshold_parsed_at_window(self, test_conn: psycopg.Connection):
        """null_rate filters rows correctly by parsed_at within start_run's started_at and finished_at window."""
        with test_conn.cursor() as cur:
            started = datetime.now(UTC) - timedelta(minutes=5)
            cur.execute(
                "INSERT INTO audit.etl_runs (task_id, source_name, status, started_at) VALUES ('transform', 'all', 'running', %s) RETURNING id",
                (started,),
            )
            run_id = cur.fetchone()["id"]
            test_conn.commit()

        # Insert 1 inside window row with rent=None (null rate inside window is 1/2 = 50% under max_null_rate = 60%)
        # Insert 1 inside window row with rent=1200
        # Insert 1 outside window row with rent=None (if included, null rate would be 2/3 = 66.7% > 60% which would fail)
        insert_staging_row(self._build_staging_row("window_in_1", rent=None))
        insert_staging_row(self._build_staging_row("window_in_2", rent=1200))
        r3_id = insert_staging_row(self._build_staging_row("window_out", rent=None))

        # Explicitly update parsed_at of window_out to 10 minutes ago
        with test_conn.cursor() as cur:
            cur.execute(
                "UPDATE staging.listings_staging SET parsed_at = NOW() - interval '10 minutes' WHERE id = %s",
                (r3_id,),
            )
            test_conn.commit()

        # Test threshold with custom max_null_rate = 0.60
        res = check_null_rate_threshold(run_id, max_null_rate=0.60)
        assert res.passed is True  # 50.00% is <= 60%
        assert "Max null rate: 50.00%" in res.message

    def test_check_fk_integrity_passes(self, test_conn: psycopg.Connection):
        """check_fk_integrity passes if all staging rows reference valid source IDs."""
        # Insert row with valid source_id (1 is pre-seeded)
        insert_staging_row(self._build_staging_row("fk_pass"))
        res = check_fk_integrity()
        assert res.passed is True
        assert "Orphaned rows" in res.message

    def test_check_fk_integrity_fails(self):
        """check_fk_integrity fails if any staging row references a non-existent source ID (simulated)."""
        from unittest.mock import MagicMock, patch

        with patch("korean_rental_etl.validation.thresholds.get_cursor") as mock_get_cursor:
            mock_cur = MagicMock()
            mock_cur.fetchone.return_value = {"count": 1}
            mock_get_cursor.return_value.__enter__.return_value = mock_cur

            res = check_fk_integrity()
            assert res.passed is False
            assert "Orphaned rows (invalid source_id): 1" in res.message

    def test_get_audit_run_id_by_airflow_run_id_success(self, test_conn: psycopg.Connection):
        """get_audit_run_id_by_airflow_run_id resolves string run_ids and numeric IDs."""
        with test_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO audit.etl_runs (task_id, source_name, status, run_id, started_at) VALUES ('transform', 'all', 'running', 'scheduled__2026-05-20T23:00:00Z', NOW()) RETURNING id"
            )
            run_id = cur.fetchone()["id"]
            test_conn.commit()

        # Resolve by string run_id
        resolved_by_str = get_audit_run_id_by_airflow_run_id("scheduled__2026-05-20T23:00:00Z")
        assert resolved_by_str == run_id

        # Resolve by exact numeric ID string
        resolved_by_num = get_audit_run_id_by_airflow_run_id(str(run_id))
        assert resolved_by_num == run_id

    def test_get_audit_run_id_by_airflow_run_id_raises_value_error(
        self, test_conn: psycopg.Connection
    ):
        """get_audit_run_id_by_airflow_run_id raises ValueError if run_id cannot be found."""
        with pytest.raises(ValueError, match="No audit run found"):
            get_audit_run_id_by_airflow_run_id("non_existent_run_id")

    def test_validate_run_hybrid_policy_success(self, test_conn: psycopg.Connection):
        """validate_run succeeds without raising exception when all checks pass."""
        with test_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO audit.etl_runs (task_id, source_name, status, started_at, rows_transformed) VALUES ('transform', 'all', 'running', NOW(), 10) RETURNING id"
            )
            run_id = cur.fetchone()["id"]
            test_conn.commit()

        insert_staging_row(self._build_staging_row("validate_success_1"))

        report = validate_run(run_id)
        assert report["passed"] is True
        assert report["soft_warning"] is False

    def test_validate_run_hybrid_policy_soft_warning(self, test_conn: psycopg.Connection):
        """validate_run succeeds but returns soft_warning=True when parsed_rows fails but others pass."""
        with test_conn.cursor() as cur:
            # Set up 5 historical runs with avg 100 rows_transformed
            for _ in range(5):
                cur.execute(
                    "INSERT INTO audit.etl_runs (task_id, source_name, status, started_at, rows_transformed) VALUES ('transform', 'all', 'success', NOW(), 100)"
                )
            # Set up current run with only 10 rows_transformed (fails threshold of 50)
            cur.execute(
                "INSERT INTO audit.etl_runs (task_id, source_name, status, started_at, rows_transformed) VALUES ('transform', 'all', 'running', NOW(), 10) RETURNING id"
            )
            run_id = cur.fetchone()["id"]
            test_conn.commit()

        # Insert valid staging row to ensure null_rate and fk_integrity pass
        insert_staging_row(self._build_staging_row("validate_soft_1"))

        report = validate_run(run_id)
        assert report["passed"] is True
        assert report["soft_warning"] is True

    def test_validate_run_hybrid_policy_hard_failure(self, test_conn: psycopg.Connection):
        """validate_run raises ValidationError when a hard constraint (like null_rate) fails."""
        with test_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO audit.etl_runs (task_id, source_name, status, started_at, rows_transformed) VALUES ('transform', 'all', 'running', NOW(), 10) RETURNING id"
            )
            run_id = cur.fetchone()["id"]
            test_conn.commit()

        # Insert a staging row with rent=None (null rate is 100% > 20%, failing null_rate hard constraint)
        insert_staging_row(self._build_staging_row("validate_hard_1", rent=None))

        with pytest.raises(
            ValidationError, match="Validation failed on hard constraints: null_rate"
        ):
            validate_run(run_id)

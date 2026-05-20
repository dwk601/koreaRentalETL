"""Integration tests for audit module."""

from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from korean_rental_etl.load.audit import finish_run, get_last_n_runs, get_run, start_run


@pytest.mark.integration
class TestAuditIntegration:
    """Integration tests for ETL run auditing against real database."""

    @pytest.fixture(autouse=True)
    def use_dict_row(self, test_conn: psycopg.Connection):
        from psycopg.rows import dict_row

        test_conn.row_factory = dict_row

    def test_start_run_creates_record_with_running_status(self, test_conn: psycopg.Connection):
        """Call start_run and verify that the run record is correctly persisted in audit.etl_runs."""
        run_db_id = start_run(
            dag_id="test_dag",
            task_id="test_task",
            run_id="test_run_123",
            source_name="svkoreans",
        )
        assert run_db_id > 0

        # Query the database to verify the record
        with test_conn.cursor() as cur:
            cur.execute("SELECT * FROM audit.etl_runs WHERE id = %s", (run_db_id,))
            row = cur.fetchone()
            assert row is not None
            assert row["dag_id"] == "test_dag"
            assert row["task_id"] == "test_task"
            assert row["run_id"] == "test_run_123"
            assert row["source_name"] == "svkoreans"
            assert row["status"] == "running"
            assert row["started_at"] is not None
            assert row["finished_at"] is None
            assert row["duration_sec"] is None

    def test_finish_run_updates_status_and_counts(self, test_conn: psycopg.Connection):
        """Call finish_run and assert that it updates the status, counts, and finished_at."""
        run_db_id = start_run(
            dag_id="test_dag",
            task_id="test_task",
            run_id="test_run_123",
            source_name="svkoreans",
        )

        finish_run(
            run_db_id=run_db_id,
            status="success",
            rows_extracted=100,
            rows_transformed=90,
            rows_loaded=80,
            rows_failed=10,
        )

        # Verify the updates in the database
        with test_conn.cursor() as cur:
            cur.execute("SELECT * FROM audit.etl_runs WHERE id = %s", (run_db_id,))
            row = cur.fetchone()
            assert row is not None
            assert row["status"] == "success"
            assert row["rows_extracted"] == 100
            assert row["rows_transformed"] == 90
            assert row["rows_loaded"] == 80
            assert row["rows_failed"] == 10
            assert row["finished_at"] is not None
            assert row["error_message"] is None

    def test_finish_run_computes_duration(self, test_conn: psycopg.Connection):
        """Verify that duration_sec is computed correctly based on start/finish times."""
        # Insert a run with a mock started_at to avoid sleeping in tests
        with test_conn.cursor() as cur:
            started_at = datetime.now(UTC) - timedelta(seconds=15)
            cur.execute(
                """
                INSERT INTO audit.etl_runs (dag_id, task_id, run_id, source_name, status, started_at)
                VALUES ('d', 't', 'r', 's', 'running', %s)
                RETURNING id
                """,
                (started_at,),
            )
            run_db_id = cur.fetchone()["id"]
            test_conn.commit()

        # Finish the run
        finish_run(run_db_id=run_db_id, status="success")

        # Verify duration
        with test_conn.cursor() as cur:
            cur.execute(
                "SELECT started_at, finished_at, duration_sec FROM audit.etl_runs WHERE id = %s",
                (run_db_id,),
            )
            row = cur.fetchone()
            assert row is not None
            expected_duration = (row["finished_at"] - row["started_at"]).total_seconds()
            assert row["duration_sec"] is not None
            assert abs(float(row["duration_sec"]) - expected_duration) < 0.5

    def test_finish_run_with_failure_records_error(self, test_conn: psycopg.Connection):
        """Call finish_run with status='failed' and verify error_message is saved."""
        run_db_id = start_run(
            dag_id="test_dag",
            task_id="test_task",
            run_id="test_run_123",
            source_name="svkoreans",
        )

        finish_run(
            run_db_id=run_db_id,
            status="failed",
            error_message="RuntimeError: Database connection lost",
        )

        # Verify database has the failure details
        with test_conn.cursor() as cur:
            cur.execute(
                "SELECT status, error_message FROM audit.etl_runs WHERE id = %s", (run_db_id,)
            )
            row = cur.fetchone()
            assert row is not None
            assert row["status"] == "failed"
            assert row["error_message"] == "RuntimeError: Database connection lost"

    def test_get_run_returns_record_or_none(self, test_conn: psycopg.Connection):
        """Verify get_run retrieves the matching dict or None on miss."""
        # Test None case
        assert get_run(999999) is None

        # Test valid record retrieval
        run_db_id = start_run(dag_id="retrieve_dag")
        run_data = get_run(run_db_id)
        assert run_data is not None
        assert run_data["id"] == run_db_id
        assert run_data["dag_id"] == "retrieve_dag"

    def test_get_last_n_runs_orders_by_started_at_desc(self, test_conn: psycopg.Connection):
        """Verify get_last_n_runs returns runs ordered DESC by started_at."""
        # Insert 3 runs with staggered started_at
        base_time = datetime.now(UTC)
        run_ids = []
        with test_conn.cursor() as cur:
            for i in range(3):
                started_at = base_time + timedelta(seconds=i * 10)
                cur.execute(
                    """
                    INSERT INTO audit.etl_runs (dag_id, task_id, run_id, source_name, status, started_at)
                    VALUES (%s, 't', 'r', 's', 'running', %s)
                    RETURNING id
                    """,
                    (f"dag_{i}", started_at),
                )
                run_ids.append(cur.fetchone()["id"])
            test_conn.commit()

        # Fetch last 3 runs
        runs = get_last_n_runs(n=3)
        assert len(runs) == 3
        # Should be ordered DESC by started_at, meaning: dag_2, dag_1, dag_0
        assert runs[0]["id"] == run_ids[2]
        assert runs[1]["id"] == run_ids[1]
        assert runs[2]["id"] == run_ids[0]

    def test_get_last_n_runs_filters_by_source_name(self, test_conn: psycopg.Connection):
        """Verify get_last_n_runs correctly filters by source name."""
        with test_conn.cursor() as cur:
            # Source A run
            cur.execute(
                """
                INSERT INTO audit.etl_runs (dag_id, source_name, status, started_at)
                VALUES ('dag_a', 'source_a', 'running', NOW())
                """
            )
            # Source B run
            cur.execute(
                """
                INSERT INTO audit.etl_runs (dag_id, source_name, status, started_at)
                VALUES ('dag_b', 'source_b', 'running', NOW())
                """
            )
            test_conn.commit()

        # Query only source_a runs
        runs_a = get_last_n_runs(n=5, source_name="source_a")
        assert len(runs_a) == 1
        assert runs_a[0]["source_name"] == "source_a"
        assert runs_a[0]["dag_id"] == "dag_a"

        # Query all runs
        runs_all = get_last_n_runs(n=5)
        assert len(runs_all) >= 2

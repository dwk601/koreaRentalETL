"""Audit module - track ETL run lifecycle."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from korean_rental_etl.db.connection import get_cursor

logger = logging.getLogger(__name__)


def start_run(
    dag_id: str | None = None,
    task_id: str | None = None,
    run_id: str | None = None,
    source_name: str | None = None,
) -> int:
    """Start a new ETL run record.

    Args:
        dag_id: Airflow DAG ID.
        task_id: Airflow task ID.
        run_id: Airflow run ID.
        source_name: Source being processed.

    Returns:
        ID of the created etl_runs row.
    """
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO audit.etl_runs (dag_id, task_id, run_id, source_name, status, started_at)
            VALUES (%s, %s, %s, %s, 'running', %s)
            RETURNING id
            """,
            (dag_id, task_id, run_id, source_name, datetime.now(UTC)),
        )
        result: dict[str, Any] | None = cur.fetchone()  # type: ignore[assignment]
        run_db_id = int(result["id"])  # type: ignore[index]

    logger.info("Started ETL run %d (dag=%s, task=%s, source=%s)", run_db_id, dag_id, task_id, source_name)
    return run_db_id


def finish_run(
    run_db_id: int,
    status: str = "success",
    rows_extracted: int = 0,
    rows_transformed: int = 0,
    rows_loaded: int = 0,
    rows_failed: int = 0,
    error_message: str | None = None,
) -> None:
    """Finish an ETL run record.

    Args:
        run_db_id: ID of the etl_runs row.
        status: Final status ('success' or 'failed').
        rows_extracted: Number of rows extracted.
        rows_transformed: Number of rows transformed.
        rows_loaded: Number of rows loaded.
        rows_failed: Number of rows that failed.
        error_message: Error message if failed.
    """
    now = datetime.now(UTC)

    with get_cursor() as cur:
        # Get started_at to compute duration
        cur.execute("SELECT started_at FROM audit.etl_runs WHERE id = %s", (run_db_id,))
        row: dict[str, Any] | None = cur.fetchone()  # type: ignore[assignment]
        started_at = row["started_at"] if row else now
        duration = (now - started_at).total_seconds()

        cur.execute(
            """
            UPDATE audit.etl_runs
            SET status = %s,
                rows_extracted = %s,
                rows_transformed = %s,
                rows_loaded = %s,
                rows_failed = %s,
                error_message = %s,
                finished_at = %s,
                duration_sec = %s
            WHERE id = %s
            """,
            (
                status,
                rows_extracted,
                rows_transformed,
                rows_loaded,
                rows_failed,
                error_message,
                now,
                duration,
                run_db_id,
            ),
        )

    logger.info(
        "Finished ETL run %d: status=%s extracted=%d transformed=%d loaded=%d failed=%d duration=%.1fs",
        run_db_id, status, rows_extracted, rows_transformed, rows_loaded, rows_failed, duration,
    )


def get_run(run_db_id: int) -> dict[str, Any] | None:
    """Get an ETL run record by ID.

    Args:
        run_db_id: ID of the etl_runs row.

    Returns:
        Dict with run data or None.
    """
    with get_cursor() as cur:
        cur.execute("SELECT * FROM audit.etl_runs WHERE id = %s", (run_db_id,))
        return cur.fetchone()  # type: ignore[return-value]


def get_last_n_runs(n: int = 5, source_name: str | None = None) -> list[dict[str, Any]]:
    """Get the last N ETL runs.

    Args:
        n: Number of runs to return.
        source_name: Optional source filter.

    Returns:
        List of run dicts.
    """
    with get_cursor() as cur:
        if source_name:
            cur.execute(
                """
                SELECT * FROM audit.etl_runs
                WHERE source_name = %s
                ORDER BY started_at DESC
                LIMIT %s
                """,
                (source_name, n),
            )
        else:
            cur.execute(
                """
                SELECT * FROM audit.etl_runs
                ORDER BY started_at DESC
                LIMIT %s
                """,
                (n,),
            )
        return cur.fetchall()  # type: ignore[return-value]

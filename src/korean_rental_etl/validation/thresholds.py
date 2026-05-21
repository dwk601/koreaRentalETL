"""Validation thresholds for ETL runs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from korean_rental_etl.db.connection import get_cursor

logger = logging.getLogger(__name__)


@dataclass
class ThresholdResult:
    """Result of a single threshold check."""

    name: str
    passed: bool
    message: str


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


def check_parsed_rows_threshold(run_id: int, threshold_ratio: float = 0.5) -> ThresholdResult:
    """Check if parsed_rows >= threshold_ratio * avg(last_5_runs).

    Args:
        run_id: Current run ID.
        threshold_ratio: Minimum ratio (default 0.5 = 50%).

    Returns:
        ThresholdResult.
    """
    with get_cursor() as cur:
        # Get current run's rows_transformed
        cur.execute("SELECT rows_transformed FROM audit.etl_runs WHERE id = %s", (run_id,))
        current = cur.fetchone()
        if not current:
            return ThresholdResult("parsed_rows", False, f"Run {run_id} not found")

        current_rows = current["rows_transformed"] or 0

        # Get average of last 5 runs (excluding current)
        cur.execute(
            """
            SELECT AVG(rows_transformed) as avg_val FROM (
                SELECT rows_transformed FROM audit.etl_runs
                WHERE id != %s AND rows_transformed IS NOT NULL
                ORDER BY id DESC LIMIT 5
            ) t
            """,
            (run_id,),
        )
        avg_result = cur.fetchone()
        avg_rows = (
            float(avg_result["avg_val"])
            if avg_result and avg_result["avg_val"] is not None
            else 0.0
        )

    if avg_rows == 0:
        # First run or no history
        return ThresholdResult("parsed_rows", True, "No historical data; skipping check")

    threshold = avg_rows * threshold_ratio
    passed = current_rows >= threshold

    message = f"Current: {current_rows}, Threshold: {threshold:.0f} (50% of avg {avg_rows:.0f})"
    return ThresholdResult("parsed_rows", passed, message)


def check_null_rate_threshold(run_id: int, max_null_rate: float = 0.20) -> ThresholdResult:
    """Check if null_rate(price|location|title) <= max_null_rate.

    Args:
        run_id: Current run ID.
        max_null_rate: Maximum allowed null rate (default 0.20 = 20%).

    Returns:
        ThresholdResult.
    """
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN rent_monthly_usd IS NULL THEN 1 END) as null_price,
                COUNT(CASE WHEN city IS NULL THEN 1 END) as null_location,
                COUNT(CASE WHEN title_ko IS NULL THEN 1 END) as null_title
            FROM staging.listings_staging
            WHERE parsed_at BETWEEN (SELECT started_at FROM audit.etl_runs WHERE id = %s)
                                AND (SELECT COALESCE(finished_at, NOW()) FROM audit.etl_runs WHERE id = %s)
            """,
            (run_id, run_id),
        )
        result = cur.fetchone()

    if not result or result["total"] == 0:
        return ThresholdResult("null_rate", True, "No rows in staging")

    total = result["total"]
    null_price = result["null_price"]
    null_location = result["null_location"]
    null_title = result["null_title"]

    rates = {
        "price": null_price / total,
        "location": null_location / total,
        "title": null_title / total,
    }

    max_rate = max(rates.values())
    passed = max_rate <= max_null_rate

    message = f"Max null rate: {max_rate:.2%} (price: {rates['price']:.2%}, location: {rates['location']:.2%}, title: {rates['title']:.2%})"
    return ThresholdResult("null_rate", passed, message)


def check_fk_integrity() -> ThresholdResult:
    """Check foreign key integrity: listings.source_id -> sources.id.

    Returns:
        ThresholdResult.
    """
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) as count FROM staging.listings_staging l
            WHERE NOT EXISTS (SELECT 1 FROM public.sources s WHERE s.id = l.source_id)
            """
        )
        orphaned = cur.fetchone()["count"]

    passed = orphaned == 0
    message = f"Orphaned rows (invalid source_id): {orphaned}"
    return ThresholdResult("fk_integrity", passed, message)


def get_audit_run_id_by_airflow_run_id(airflow_run_id: str, task_id: str = "transform") -> int:
    """Find the audit run DB ID for a given Airflow run_id or numeric DB ID."""
    with get_cursor() as cur:
        # First, try treating it as an exact numeric DB ID
        try:
            db_id = int(airflow_run_id)
            cur.execute("SELECT id FROM audit.etl_runs WHERE id = %s", (db_id,))
            if cur.fetchone():
                return db_id
        except ValueError:
            pass

        # Otherwise, query by run_id string
        cur.execute(
            "SELECT id FROM audit.etl_runs WHERE run_id = %s AND task_id = %s ORDER BY id DESC LIMIT 1",
            (airflow_run_id, task_id),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(
                f"No audit run found for Airflow run_id '{airflow_run_id}' and task '{task_id}'"
            )
        return int(row["id"])


def validate_run(run_id: int) -> dict[str, Any]:
    """Run all validation checks.

    Args:
        run_id: ETL run ID.

    Returns:
        Dict with results and overall pass/fail.

    Raises:
        ValidationError if any hard check fails.
    """
    parsed_rows_res = check_parsed_rows_threshold(run_id)
    null_rate_res = check_null_rate_threshold(run_id)
    fk_integrity_res = check_fk_integrity()

    # Apply hybrid policy: parsed_rows is soft, others are hard.
    soft_warning = False
    if not parsed_rows_res.passed:
        logger.warning("Soft validation warning (parsed_rows): %s", parsed_rows_res.message)
        soft_warning = True

    # Check hard failures
    hard_failed = []
    if not null_rate_res.passed:
        hard_failed.append(null_rate_res.name)
    if not fk_integrity_res.passed:
        hard_failed.append(fk_integrity_res.name)

    results = [parsed_rows_res, null_rate_res, fk_integrity_res]

    report = {
        "run_id": run_id,
        "checks": [{"name": r.name, "passed": r.passed, "message": r.message} for r in results],
        "passed": len(hard_failed) == 0,
        "soft_warning": soft_warning,
    }

    if hard_failed:
        raise ValidationError(f"Validation failed on hard constraints: {', '.join(hard_failed)}")

    return report

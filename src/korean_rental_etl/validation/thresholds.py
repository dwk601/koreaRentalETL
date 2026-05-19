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
        # Get current run's parsed_rows
        cur.execute("SELECT rows_parsed FROM audit.etl_runs WHERE id = %s", (run_id,))
        current = cur.fetchone()
        if not current:
            return ThresholdResult("parsed_rows", False, f"Run {run_id} not found")

        current_rows = current[0] or 0

        # Get average of last 5 runs (excluding current)
        cur.execute(
            """
            SELECT AVG(rows_parsed) FROM (
                SELECT rows_parsed FROM audit.etl_runs
                WHERE id != %s AND rows_parsed IS NOT NULL
                ORDER BY id DESC LIMIT 5
            ) t
            """,
            (run_id,),
        )
        avg_result = cur.fetchone()
        avg_rows = avg_result[0] if avg_result and avg_result[0] else 0

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
            WHERE run_id = %s
            """,
            (run_id,),
        )
        result = cur.fetchone()

    if not result or result[0] == 0:
        return ThresholdResult("null_rate", True, "No rows in staging")

    total, null_price, null_location, null_title = result
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
            SELECT COUNT(*) FROM staging.listings_staging l
            WHERE NOT EXISTS (SELECT 1 FROM public.sources s WHERE s.id = l.source_id)
            """
        )
        orphaned = cur.fetchone()[0]

    passed = orphaned == 0
    message = f"Orphaned rows (invalid source_id): {orphaned}"
    return ThresholdResult("fk_integrity", passed, message)


def validate_run(run_id: int) -> dict[str, Any]:
    """Run all validation checks.

    Args:
        run_id: ETL run ID.

    Returns:
        Dict with results and overall pass/fail.

    Raises:
        ValidationError if any check fails.
    """
    results = [
        check_parsed_rows_threshold(run_id),
        check_null_rate_threshold(run_id),
        check_fk_integrity(),
    ]

    report = {
        "run_id": run_id,
        "checks": [{"name": r.name, "passed": r.passed, "message": r.message} for r in results],
        "passed": all(r.passed for r in results),
    }

    if not report["passed"]:
        failed = [r.name for r in results if not r.passed]
        raise ValidationError(f"Validation failed: {', '.join(failed)}")

    return report

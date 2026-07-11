"""Loader - batch upsert into public.listings with audit."""

from __future__ import annotations

import logging
from typing import Any

from korean_rental_etl.db.connection import get_connection, get_cursor
from korean_rental_etl.load.audit import finish_run, start_run

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


def upsert_batch(rows: list[dict[str, Any]], run_db_id: int) -> tuple[int, int, list[int]]:
    """Upsert a batch of staging rows into public.listings in a single transaction.

    Args:
        rows: List of dicts with listing data.
        run_db_id: Audit run ID.

    Returns:
        Tuple of (rows_upserted, rows_failed, list_of_staging_ids).
    """
    if not rows:
        return 0, 0, []

    upserted = 0
    failed = 0
    loaded_staging_ids = []

    try:
        # Psycopg pipeline batches protocol traffic while savepoints retain the
        # existing per-row success/failure semantics.
        with get_connection() as conn, conn.pipeline(), conn.transaction(), conn.cursor() as cur:
            for row in rows:
                try:
                    with conn.transaction():
                        cur.execute(
                            """
                                    INSERT INTO public.listings (
                                        source_id, source_listing_id, url,
                                        title_ko, body_ko,
                                        rent_monthly_usd, deposit_usd, lease_type, currency_raw, price_raw_ko,
                                        posted_at_utc, city, state_or_province, country, address_raw,
                                        phone, kakao_id, email, category,
                                        is_active, last_seen_at
                                    ) VALUES (
                                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, NOW()
                                    )
                                    ON CONFLICT (source_id, source_listing_id) DO UPDATE SET
                                        title_ko = EXCLUDED.title_ko,
                                        body_ko = EXCLUDED.body_ko,
                                        rent_monthly_usd = EXCLUDED.rent_monthly_usd,
                                        deposit_usd = EXCLUDED.deposit_usd,
                                        lease_type = EXCLUDED.lease_type,
                                        price_raw_ko = EXCLUDED.price_raw_ko,
                                        posted_at_utc = EXCLUDED.posted_at_utc,
                                        city = EXCLUDED.city,
                                        state_or_province = EXCLUDED.state_or_province,
                                        country = EXCLUDED.country,
                                        address_raw = EXCLUDED.address_raw,
                                        phone = EXCLUDED.phone,
                                        kakao_id = EXCLUDED.kakao_id,
                                        email = EXCLUDED.email,
                                        category = EXCLUDED.category,
                                        is_active = TRUE,
                                        last_seen_at = NOW(),
                                        updated_at = NOW()
                                    RETURNING id
                                    """,
                            (
                                row.get("source_id"),
                                row.get("source_listing_id"),
                                row.get("url"),
                                row.get("title_ko"),
                                row.get("body_ko"),
                                row.get("rent_monthly_usd"),
                                row.get("deposit_usd"),
                                row.get("lease_type"),
                                row.get("currency_raw"),
                                row.get("price_raw_ko"),
                                row.get("posted_at_utc"),
                                row.get("city"),
                                row.get("state_or_province"),
                                row.get("country"),
                                row.get("address_raw"),
                                row.get("phone"),
                                row.get("kakao_id"),
                                row.get("email"),
                                row.get("category"),
                            ),
                        )
                        result = cur.fetchone()
                        if result:
                            upserted += 1
                            if "id" in row:
                                loaded_staging_ids.append(row["id"])
                except Exception as e:
                    logger.warning("Failed to upsert row %s: %s", row.get("source_listing_id"), e)
                    failed += 1
    except Exception as e:
        logger.error("Batch transaction failed: %s", e)
        raise

    if run_db_id and (upserted > 0 or failed > 0):
        try:
            with get_cursor() as cur:
                cur.execute(
                    """
                    UPDATE audit.etl_runs
                    SET rows_loaded = rows_loaded + %s,
                        rows_failed = rows_failed + %s
                    WHERE id = %s
                    """,
                    (upserted, failed, run_db_id),
                )
        except Exception as e:
            logger.warning("Failed to update audit.etl_runs for load counts: %s", e)

    logger.info("Upserted %d/%d listings", upserted, len(rows))
    return upserted, failed, loaded_staging_ids


def load_from_staging(
    source_id: int | None = None,
    dag_id: str | None = None,
    run_id: str | None = None,
) -> tuple[int, int]:
    """Load all unparsed staging rows into public.listings.

    Args:
        source_id: Optional source filter.
        dag_id: Workflow ID retained in the existing audit schema.
        run_id: Workflow run ID.

    Returns:
        Tuple of (rows_loaded, rows_failed).
    """
    run_db_id = start_run(
        dag_id=dag_id,
        task_id="load",
        run_id=run_id,
        source_name="all" if source_id is None else str(source_id),
    )

    with get_cursor() as cur:
        if source_id:
            cur.execute(
                """
                SELECT * FROM staging.listings_staging
                WHERE source_id = %s AND loaded_at IS NULL
                LIMIT %s
                """,
                (source_id, BATCH_SIZE),
            )
        else:
            cur.execute(
                """
                SELECT * FROM staging.listings_staging
                WHERE loaded_at IS NULL
                LIMIT %s
                """,
                (BATCH_SIZE,),
            )
        rows: list[dict[str, Any]] = cur.fetchall()  # type: ignore[assignment]

    loaded = 0
    failed = 0
    try:
        batch_loaded, batch_failed, staging_ids = upsert_batch(rows, run_db_id)
        loaded += batch_loaded
        failed += batch_failed

        if staging_ids:
            with get_cursor() as cur:
                cur.execute(
                    "UPDATE staging.listings_staging SET loaded_at = NOW() WHERE id = ANY(%s)",
                    (staging_ids,),
                )

        finish_run(run_db_id, status="success", rows_loaded=loaded, rows_failed=failed)
    except Exception as e:
        finish_run(
            run_db_id, status="failed", rows_loaded=loaded, rows_failed=failed, error_message=str(e)
        )
        raise

    return loaded, failed

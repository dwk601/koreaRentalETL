"""Transform pipeline orchestrator - parse → normalize → classify → geocode → staging."""

from __future__ import annotations

import logging
from typing import Any

from korean_rental_etl.db.connection import get_cursor
from korean_rental_etl.extract.raw_writer import get_unparsed_pages
from korean_rental_etl.load.audit import finish_run, start_run
from korean_rental_etl.transform.classifier import classify
from korean_rental_etl.transform.dedup.fuzzy_layer import find_duplicates
from korean_rental_etl.transform.geocoder import geocode
from korean_rental_etl.transform.normalizers.contact import normalize_contact
from korean_rental_etl.transform.normalizers.date import normalize_date
from korean_rental_etl.transform.normalizers.location import normalize_location
from korean_rental_etl.transform.normalizers.price import normalize_price
from korean_rental_etl.transform.parsers.gtksa import GTKSAParser
from korean_rental_etl.transform.parsers.illinoisksa import IllinoisksaParser
from korean_rental_etl.transform.parsers.ktown_koreadaily import KtownKoreadailyParser
from korean_rental_etl.transform.parsers.missyusa import MissyusaParser
from korean_rental_etl.transform.parsers.radiokorea import RadiokoreaParser
from korean_rental_etl.transform.parsers.svkoreans import SVKoreansParser
from korean_rental_etl.transform.staging_writer import get_recent_unloaded, insert_staging_row

logger = logging.getLogger(__name__)


def _get_parser(
    source_name: str,
) -> (
    SVKoreansParser
    | GTKSAParser
    | KtownKoreadailyParser
    | MissyusaParser
    | RadiokoreaParser
    | IllinoisksaParser
    | None
):
    """Get parser for a source."""
    parsers: dict[
        str,
        SVKoreansParser
        | GTKSAParser
        | KtownKoreadailyParser
        | MissyusaParser
        | RadiokoreaParser
        | IllinoisksaParser,
    ] = {
        "svkoreans": SVKoreansParser(),
        "gtksa": GTKSAParser(),
        "ktown_koreadaily": KtownKoreadailyParser(),
        "missyusa": MissyusaParser(),
        "radiokorea": RadiokoreaParser(),
        "illinoisksa": IllinoisksaParser(),
    }
    return parsers.get(source_name)


def get_source_id_by_name(source_name: str) -> int:
    """Get source ID from source name."""
    with get_cursor() as cur:
        cur.execute("SELECT id FROM public.sources WHERE name = %s", (source_name,))
        result = cur.fetchone()
        if not result:
            raise ValueError(f"Source not found: {source_name}")
        return int(result["id"])


def transform_row(
    source_name: str, source_id: int, raw_page: dict[str, Any]
) -> dict[str, Any] | None:
    """Transform a single raw page into a staging row.

    Args:
        source_name: Name of the source (e.g., 'svkoreans').
        source_id: ID of the source.
        raw_page: Dict with html_content, url, content_hash.

    Returns:
        Dict ready for insert_staging_row, or None if parse failed.
    """
    parser = _get_parser(source_name)
    if not parser:
        logger.warning("No parser for source: %s", source_name)
        return None

    # Parse
    try:
        parsed = parser.parse_detail(raw_page["html_content"], raw_page["url"])
    except Exception as e:
        logger.warning("Parse error for %s: %s", source_name, e)
        return None

    # Check for required fields
    if not parsed.get("title_ko") and not parsed.get("body_ko") and not parsed.get("raw_price"):
        logger.debug("Skipping row with no title_ko, body_ko, and raw_price")
        return None

    # Normalize price
    price_norm = normalize_price(parsed.get("raw_price", ""))

    # Normalize date
    date_norm = normalize_date(parsed.get("raw_posted_at", ""))

    # Normalize location
    location_norm = normalize_location(parsed.get("raw_location", ""))

    # Normalize contact
    contact_norm = normalize_contact(parsed.get("contact_block", ""))

    # Classify
    category = classify(
        title_ko=parsed.get("title_ko", ""),
        body_ko=parsed.get("body_ko", ""),
    )

    # Geocode (non-fatal if fails)
    lat = None
    lon = None
    if location_norm.get("address_raw"):
        try:
            geo_result = geocode(
                location_norm["address_raw"],
                location_norm.get("city"),
                location_norm.get("country", "US"),
            )
            lat = geo_result.get("lat")
            lon = geo_result.get("lon")
        except Exception as e:
            logger.warning("Geocoding failed: %s", e)

    # Build staging row
    row = {
        "source_id": source_id,
        "source_listing_id": parsed.get("source_listing_id", ""),
        "url": parsed.get("url", ""),
        "content_hash": parsed.get("content_hash", ""),
        "title_ko": parsed.get("title_ko", ""),
        "body_ko": parsed.get("body_ko", ""),
        "raw_price": parsed.get("raw_price", ""),
        "raw_location": parsed.get("raw_location", ""),
        "raw_posted_at": parsed.get("raw_posted_at", ""),
        "contact_block": parsed.get("contact_block", ""),
        "rent_monthly_usd": price_norm.get("rent_monthly_usd"),
        "deposit_usd": price_norm.get("deposit_usd"),
        "lease_type": price_norm.get("lease_type"),
        "currency_raw": price_norm.get("currency_raw"),
        "price_raw_ko": price_norm.get("price_raw_ko"),
        "posted_at_utc": date_norm.get("posted_at_utc"),
        "city": location_norm.get("city"),
        "state_or_province": location_norm.get("state_or_province"),
        "country": location_norm.get("country"),
        "address_raw": location_norm.get("address_raw"),
        "phone": contact_norm.get("phone"),
        "kakao_id": contact_norm.get("kakao_id"),
        "email": contact_norm.get("email"),
        "category": category,
        "lat": lat,
        "lon": lon,
        "is_duplicate": False,
        "duplicate_of": None,
        "canonical_id": None,
        "errors": {},
    }

    return row


def run(
    source_name: str | None = None,
    source_id: int | None = None,
    limit: int = 500,
    dag_id: str | None = None,
    run_id: str | None = None,
) -> tuple[int, int]:
    """Run the transform pipeline for one or all sources.

    Args:
        source_name: Source name (e.g., 'svkoreans'). If None, processes all sources.
        source_id: Source ID. If None, looks up from source_name.
        limit: Max rows to process per source.
        dag_id: Optional workflow ID retained in the audit schema.
        run_id: Optional workflow run ID string.

    Returns:
        Tuple of (rows_parsed, rows_failed).
    """
    # Determine sources to process
    if source_name:
        if not source_id:
            source_id = get_source_id_by_name(source_name)
        sources_to_process: list[tuple[str, int]] = [(source_name, source_id)]
    else:
        # Get all active sources
        with get_cursor() as cur:
            cur.execute("SELECT id, name FROM public.sources WHERE is_active = TRUE")
            sources_to_process = [(row["name"], row["id"]) for row in cur.fetchall()]

    # Start audit run
    run_db_id = start_run(
        dag_id=dag_id,
        task_id="transform",
        run_id=run_id,
        source_name=source_name or "all",
    )

    rows_parsed = 0
    rows_failed = 0
    batch_rows: list[dict[str, Any]] = []

    try:
        for src_name, src_id in sources_to_process:
            logger.info("Processing source: %s (id=%d)", src_name, src_id)

            # Get unparsed pages
            unparsed = get_unparsed_pages(src_id, limit)
            logger.info("Found %d unparsed pages for %s", len(unparsed), src_name)

            for raw_page in unparsed:
                # Transform
                row = transform_row(src_name, src_id, raw_page)
                if not row:
                    rows_failed += 1
                    continue

                batch_rows.append(row)

        # Get recent unloaded staging rows for fuzzy dedup
        recent = get_recent_unloaded(source_id=None, days=7)
        logger.info("Found %d recent unloaded staging rows for dedup", len(recent))

        # Assign synthetic negative ids to batch rows so fuzzy_layer can flag intra-batch
        # duplicates with a canonical_id that we can resolve post-insert.
        # Negative ids cannot collide with real staging ids (always positive).
        for i, batch_row in enumerate(batch_rows):
            batch_row["id"] = -(i + 1)

        # Run fuzzy dedup on batch + recent
        dedup_input: list[dict[str, Any]] = batch_rows + recent
        dedup_output = find_duplicates(dedup_input)
        n_dups = sum(1 for r in dedup_output if r.get("is_duplicate"))
        n_intra = sum(
            1
            for r in dedup_output
            if r.get("is_duplicate")
            and isinstance(r.get("canonical_id"), int)
            and r["canonical_id"] < 0
        )
        logger.info(
            "[transform] dedup: %d duplicates within batch, %d duplicates against recent staging",
            n_intra,
            n_dups - n_intra,
        )

        # Build map from synthetic batch id -> (source_id, source_listing_id) for post-insert resolution
        synthetic_to_key: dict[int, tuple[int, str]] = {
            row["id"]: (row["source_id"], row["source_listing_id"])
            for row in batch_rows
            if isinstance(row.get("id"), int) and row["id"] < 0
        }

        # Strip synthetic id before insert (insert_staging_row uses BIGSERIAL)
        # and capture intra-batch canonical references for post-insert resolution.
        intra_batch_refs: list[tuple[tuple[int, str], tuple[int, str]]] = []
        batch_ids = {id(row) for row in batch_rows}
        for row in dedup_output:
            if id(row) not in batch_ids:
                continue  # recent staging rows, already in DB
            row.pop("id", None)
            cid = row.get("canonical_id")
            if isinstance(cid, int) and cid < 0:
                # intra-batch duplicate: capture (dup_key, canonical_key) and clear canonical_id
                dup_key = (row["source_id"], row["source_listing_id"])
                canonical_key = synthetic_to_key.get(cid)
                if canonical_key is not None:
                    intra_batch_refs.append((dup_key, canonical_key))
                row["canonical_id"] = None  # will be resolved via UPDATE post-insert

        # Insert batch rows
        for row in dedup_output:
            if id(row) not in batch_ids:
                continue

            try:
                insert_staging_row(row)
                rows_parsed += 1
            except Exception as e:
                logger.error("Failed to insert staging row: %s", e)
                rows_failed += 1

        # Resolve intra-batch canonical_ids: build (source_id, source_listing_id) -> staging_id map
        # and UPDATE duplicate rows' canonical_id.
        if intra_batch_refs:
            with get_cursor() as cur:
                # Fetch staging ids for all keys we care about
                wanted_keys = {k for pair in intra_batch_refs for k in pair}
                placeholders = ",".join(["(%s,%s)"] * len(wanted_keys))
                params: list[Any] = []
                for sid, slid in wanted_keys:
                    params.extend([sid, slid])
                cur.execute(
                    f"""
                    SELECT id, source_id, source_listing_id
                    FROM staging.listings_staging
                    WHERE (source_id, source_listing_id) IN ({placeholders})
                    """,
                    params,
                )
                key_to_id: dict[tuple[int, str], int] = {
                    (r["source_id"], r["source_listing_id"]): r["id"] for r in cur.fetchall()
                }
                # UPDATE per duplicate
                for dup_key, canonical_key in intra_batch_refs:
                    canonical_id = key_to_id.get(canonical_key)
                    if canonical_id is None:
                        continue
                    cur.execute(
                        """
                        UPDATE staging.listings_staging
                        SET canonical_id = %s
                        WHERE source_id = %s AND source_listing_id = %s
                        """,
                        (canonical_id, dup_key[0], dup_key[1]),
                    )
            logger.info("Resolved %d intra-batch canonical_id references", len(intra_batch_refs))

        # Finish audit run
        finish_run(
            run_db_id,
            status="success",
            rows_transformed=rows_parsed,
            rows_failed=rows_failed,
        )
        logger.info("Transform complete: %d parsed, %d failed", rows_parsed, rows_failed)

    except Exception as e:
        logger.error("Transform pipeline failed: %s", e)
        finish_run(run_db_id, status="failed", error_message=str(e))
        raise

    return rows_parsed, rows_failed

"""Database models as dataclasses for type-safe query results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal


@dataclass
class Source:
    """Represents a row in public.sources."""

    id: int
    name: str
    display_name: str | None
    base_url: str
    fetcher_type: str
    schedule_cron: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class ScrapedPage:
    """Represents a row in raw.scraped_pages."""

    id: int
    source_id: int
    url: str
    html_content: str | None
    content_hash: str
    http_status: int | None
    fetched_at: datetime


@dataclass
class Listing:
    """Represents a row in public.listings."""

    id: int
    source_id: int
    source_listing_id: str
    url: str
    title_ko: str | None
    title_en: str | None
    body_ko: str | None
    body_en: str | None
    rent_monthly_usd: Decimal | None
    deposit_usd: Decimal | None
    lease_type: str | None
    currency_raw: str | None
    price_raw_ko: str | None
    posted_at_utc: datetime | None
    first_seen_at: datetime
    last_seen_at: datetime
    city: str | None
    state_or_province: str | None
    country: str | None
    address_raw: str | None
    phone: str | None
    kakao_id: str | None
    email: str | None
    category: str | None
    is_canonical: bool
    duplicate_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class EtlRun:
    """Represents a row in audit.etl_runs."""

    id: int
    dag_id: str | None
    task_id: str | None
    run_id: str | None
    source_name: str | None
    status: str
    rows_extracted: int
    rows_transformed: int
    rows_loaded: int
    rows_failed: int
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None
    duration_sec: Decimal | None

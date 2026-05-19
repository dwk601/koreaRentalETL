-- Korean Rental ETL - Schema Migration 001
-- Creates schemas, extensions, and all core tables

-- Extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Schemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS audit;

-- ============================================================
-- Sources registry
-- ============================================================
CREATE TABLE IF NOT EXISTS public.sources (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(50) NOT NULL UNIQUE,
    display_name    VARCHAR(100),
    base_url        TEXT NOT NULL,
    fetcher_type    VARCHAR(30) NOT NULL DEFAULT 'StealthyFetcher',
    schedule_cron   VARCHAR(50),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed sources from config
INSERT INTO public.sources (name, display_name, base_url, fetcher_type, schedule_cron, is_active)
VALUES
    ('svkoreans',       'SV Koreans',           'https://svkoreans.com/rent_housing',           'StealthyFetcher', '0 */6 * * *', TRUE),
    ('gtksa',           'GTKSA',                'https://gtksa.net/bbs/board.php?bo_table=rent','StealthyFetcher', '0 */6 * * *', TRUE),
    ('missyusa',        'MissyUSA',             'https://missyusa.com/town9',                   'StealthyFetcher', '0 */6 * * *', TRUE),
    ('ktown_koreadaily','Korea Daily K-Town',   'https://ktown.koreadaily.com/ad_rent/rentlist','StealthyFetcher', '0 */6 * * *', TRUE),
    ('radiokorea',      'Radio Korea',          'https://m.radiokorea.com/c_realestate',        'DynamicFetcher',  '0 */6 * * *', TRUE),
    ('hanintown',       'Hanin Town',           'https://hanintown.com',                        'StealthyFetcher', NULL,          FALSE)
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- Raw HTML staging
-- ============================================================
CREATE TABLE IF NOT EXISTS raw.scraped_pages (
    id              BIGSERIAL PRIMARY KEY,
    source_id       INTEGER NOT NULL REFERENCES public.sources(id),
    url             TEXT NOT NULL,
    html_content    TEXT,
    content_hash    VARCHAR(64) NOT NULL,  -- SHA-256
    http_status     INTEGER,
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_id, url, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_scraped_pages_source_url ON raw.scraped_pages (source_id, url);
CREATE INDEX IF NOT EXISTS idx_scraped_pages_fetched_at ON raw.scraped_pages (fetched_at);

-- ============================================================
-- Staging parsed listings
-- ============================================================
CREATE TABLE IF NOT EXISTS staging.listings_staging (
    id                  BIGSERIAL PRIMARY KEY,
    source_id           INTEGER NOT NULL REFERENCES public.sources(id),
    source_listing_id   VARCHAR(100) NOT NULL,
    url                 TEXT NOT NULL,
    content_hash        VARCHAR(64),

    -- Bilingual title/body
    title_ko            TEXT,
    title_en            TEXT,
    body_ko             TEXT,
    body_en             TEXT,

    -- Raw fields (Korean)
    raw_price           TEXT,
    raw_location        TEXT,
    raw_posted_at       TEXT,
    contact_block       TEXT,

    -- Normalized fields
    rent_monthly_usd    NUMERIC(10,2),
    deposit_usd         NUMERIC(10,2),
    lease_type          VARCHAR(30),     -- monthly, jeonse, short_term, lease
    currency_raw        VARCHAR(10),
    price_raw_ko        TEXT,

    posted_at_utc       TIMESTAMPTZ,

    city                VARCHAR(100),
    state_or_province   VARCHAR(100),
    country             VARCHAR(10),
    address_raw         TEXT,

    phone               VARCHAR(30),
    kakao_id            VARCHAR(50),
    email               VARCHAR(100),

    category            VARCHAR(30),     -- apartment, house, condo, etc.

    -- PostGIS point
    geo_point           GEOMETRY(Point, 4326),

    -- Dedup tracking
    is_duplicate        BOOLEAN DEFAULT FALSE,
    duplicate_of        BIGINT,
    canonical_id        BIGINT,

    -- Metadata
    parsed_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    loaded_at           TIMESTAMPTZ,
    errors              JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_staging_source_listing ON staging.listings_staging (source_id, source_listing_id);
CREATE INDEX IF NOT EXISTS idx_staging_content_hash ON staging.listings_staging (content_hash);
CREATE INDEX IF NOT EXISTS idx_staging_loaded_at ON staging.listings_staging (loaded_at);

-- ============================================================
-- Final clean listings table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.listings (
    id                  BIGSERIAL PRIMARY KEY,
    source_id           INTEGER NOT NULL REFERENCES public.sources(id),
    source_listing_id   VARCHAR(100) NOT NULL,
    url                 TEXT NOT NULL,

    -- Bilingual
    title_ko            TEXT,
    title_en            TEXT,
    body_ko             TEXT,
    body_en             TEXT,

    -- Pricing
    rent_monthly_usd    NUMERIC(10,2),
    deposit_usd         NUMERIC(10,2),
    lease_type          VARCHAR(30),
    currency_raw        VARCHAR(10),
    price_raw_ko        TEXT,

    -- Dates
    posted_at_utc       TIMESTAMPTZ,
    first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Location
    city                VARCHAR(100),
    state_or_province   VARCHAR(100),
    country             VARCHAR(10),
    address_raw         TEXT,
    geo_point           GEOMETRY(Point, 4326),

    -- Contact
    phone               VARCHAR(30),
    kakao_id            VARCHAR(50),
    email               VARCHAR(100),

    -- Category
    category            VARCHAR(30),

    -- Dedup
    is_canonical        BOOLEAN DEFAULT TRUE,
    duplicate_count     INTEGER DEFAULT 0,

    -- Status
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,

    -- Metadata
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (source_id, source_listing_id)
);

-- 8 indexes as specified in plan
CREATE INDEX IF NOT EXISTS idx_listings_source_id ON public.listings (source_id);
CREATE INDEX IF NOT EXISTS idx_listings_city ON public.listings (city);
CREATE INDEX IF NOT EXISTS idx_listings_category ON public.listings (category);
CREATE INDEX IF NOT EXISTS idx_listings_is_active ON public.listings (is_active);
CREATE INDEX IF NOT EXISTS idx_listings_posted_at ON public.listings (posted_at_utc);
CREATE INDEX IF NOT EXISTS idx_listings_last_seen ON public.listings (last_seen_at);
CREATE INDEX IF NOT EXISTS idx_listings_geo_point ON public.listings USING GIST (geo_point);
CREATE INDEX IF NOT EXISTS idx_listings_korean_fts ON public.listings USING GIN ((title_ko || ' ' || body_ko || ' ' || address_raw) gin_trgm_ops);

-- ============================================================
-- Audit table for ETL runs
-- ============================================================
CREATE TABLE IF NOT EXISTS audit.etl_runs (
    id                  BIGSERIAL PRIMARY KEY,
    dag_id              VARCHAR(100),
    task_id             VARCHAR(100),
    run_id              VARCHAR(100),
    source_name         VARCHAR(50),
    status              VARCHAR(20) NOT NULL DEFAULT 'running',  -- running, success, failed
    rows_extracted      INTEGER DEFAULT 0,
    rows_transformed    INTEGER DEFAULT 0,
    rows_loaded         INTEGER DEFAULT 0,
    rows_failed         INTEGER DEFAULT 0,
    error_message       TEXT,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at         TIMESTAMPTZ,
    duration_sec        NUMERIC(10,2)
);

CREATE INDEX IF NOT EXISTS idx_etl_runs_run_id ON audit.etl_runs (run_id);
CREATE INDEX IF NOT EXISTS idx_etl_runs_started_at ON audit.etl_runs (started_at);

# Korean Rental ETL

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Sources](#sources)
- [Quick Start](#quick-start)
- [Operator's Guide](#operators-guide)
  - [Prerequisites](#prerequisites)
  - [Configuration](#configuration)
  - [Service Ports](#service-ports)
  - [Deploying](#deploying)
  - [Verifying the Deployment](#verifying-the-deployment)
  - [Triggering DAGs](#triggering-dags)
  - [Viewing Logs](#viewing-logs)
  - [Troubleshooting](#troubleshooting)
  - [Before Exposing Publicly](#before-exposing-publicly)
- [Developer's Guide](#developers-guide)
  - [Local Setup](#local-setup)
  - [Make Targets](#make-targets)
  - [Project Structure](#project-structure)
  - [Running Tests](#running-tests)
  - [CLI Command Reference](#cli-command-reference)
  - [Adding a New Source](#adding-a-new-source)
  - [Database Schema](#database-schema)
  - [Migrations](#migrations)
- [DAG Schedules](#dag-schedules)
- [License](#license)

## Overview

ETL pipeline for scraping, transforming, and loading Korean rental listings from community boards. Extracts HTML from six sources, parses and normalizes Korean text, geocodes addresses, deduplicates listings, and loads into PostgreSQL with full-text search. Orchestrated by Apache Airflow on a 6-hour schedule with audit logging and validation thresholds.

## Architecture

```mermaid
flowchart LR
    A["Source sites<br/>(svkoreans, gtksa, etc.)"] -->|StealthyFetcher /<br/>DynamicFetcher| E["Extract"]
    E --> R[("raw.scraped_pages")]
    R --> T["Transform<br/>parse · normalize<br/>geocode · dedup"]
    T --> S[("staging.<br/>listings_staging")]
    S --> L["Load<br/>upsert"]
    L --> P[("public.listings")]
    P --> V["Validate<br/>thresholds"]
    V --> N["Notify<br/>SMTP"]
    E -.->|dag_id, run_id| AU[("audit.<br/>etl_runs")]
    T -.->|dag_id, run_id| AU
    L -.->|dag_id, run_id| AU
```

**Extract**: Scrapling-based scrapers with Cloudflare bypass (StealthyFetcher, DynamicFetcher).  
**Transform**: Korean text normalization, Nominatim geocoding, fuzzy + hash deduplication, trigram FTS indexing.  
**Load**: PostgreSQL with PostGIS and pg_trgm extensions; upsert with audit trail.  
**Orchestration**: Apache Airflow LocalExecutor; 6-hour schedule with email alerts via MailHog (dev) or SMTP relay (prod).

### Extract: 30-Day Cutoff and Pagination

The extract step implements a 30-day cutoff to avoid filling the warehouse with stale rentals. Each scraper:

1. **Parses list-page dates** from each listing row (e.g., "05.19" for May 19, "16:53" for today's time-only format).
2. **Paginates through list pages** using `?page=N` query parameters, walking pages until a row with `post_date < today - EXTRACT_CUTOFF_DAYS` is encountered.
3. **Stops pagination early** when a stale row is found, saving bandwidth and API calls.
4. **Filters at extract time** via `BaseScraper.extract()`, skipping detail-page fetches for stale listings.

**Initial vs. steady-state behavior:**
- **Initial run** (empty database): Backfills up to 30 days of history by walking all pages until cutoff.
- **Steady-state run** (6-hour schedule): Pulls only new listings (typically page 1) because older URLs are cached in Redis (14-day TTL).

**Deduplication layers** (unchanged):
- Redis URL cache (14-day sliding TTL) skips re-fetching already-seen URLs.
- `raw.scraped_pages` ON CONFLICT DO NOTHING on `(source_id, url, content_hash)` prevents duplicate HTML storage.
- `staging.listings_staging` UNIQUE `(source_id, source_listing_id)` + UPSERT on `public.listings` ensures canonical dedup.

Configure the cutoff window via `EXTRACT_CUTOFF_DAYS` (default 30 days).

## Sources

| Name | URL | Status |
|------|-----|--------|
| svkoreans | https://svkoreans.com/rent_housing | Active |
| gtksa | https://gtksa.net/bbs/board.php?bo_table=rent | Active |
| missyusa | https://missyusa.com/town9 | Active |
| ktown_koreadaily | https://ktown.koreadaily.com/ad_rent/rentlist | Active |
| radiokorea | https://m.radiokorea.com/c_realestate | Active |
| hanintown | https://hanintown.com | Disabled |

## Quick Start

```bash
# Clone and configure
git clone <repo-url>
cd koreaRentalETL
cp .env.example .env
# Edit .env and set POSTGRES_PASSWORD, AIRFLOW_DB_PASSWORD, AIRFLOW_ADMIN_PASSWORD

# Start the stack
docker compose up -d --build

# Access services
# Airflow WebUI:  http://localhost:8080 (admin/admin by default)
# MailHog:        http://localhost:8025
# PostgreSQL:     localhost:5432
# Redis:          localhost:6379
```

## Operator's Guide

### Prerequisites

- Ubuntu 22.04 LTS or later
- Docker Engine ≥ 24.0
- Docker Compose v2 plugin
- Ports 8080, 5432, 5433, 6379, 1025, 8025 available

### Configuration

Copy `.env.example` to `.env` and edit the following keys:

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `POSTGRES_PASSWORD` | Yes | *None* | PostgreSQL app DB password (fail-fast check) |
| `AIRFLOW_DB_PASSWORD` | Yes | *None* | Airflow metadata DB password (fail-fast check) |
| `AIRFLOW_ADMIN_PASSWORD` | Yes | *None* | Airflow web UI admin password (fail-fast check) |
| `AIRFLOW_HOST` | Yes | `localhost` | The hostname routing the Airflow WebUI (Coolify/Traefik) |
| `POSTGRES_USER` | No | `etl_user` | PostgreSQL app DB user |
| `POSTGRES_DB` | No | `korean_rental` | PostgreSQL app DB name |
| `POSTGRES_PORT` | No | `5432` | PostgreSQL app DB port |
| `REDIS_PORT` | No | `6379` | Redis port |
| `NOMINATIM_USER_AGENT` | No | `korean-rental-etl/0.1.0 (contact@example.com)` | Nominatim geocoding user agent |
| `NOMINATIM_RATE_LIMIT_PER_SEC` | No | `1` | Nominatim requests per second |
| `DOWNLOAD_DELAY_SEC` | No | `2.0` | Scraper delay between requests |
| `CONCURRENT_REQUESTS` | No | `2` | Scraper concurrent request limit |
| `MAX_RETRIES` | No | `3` | Scraper retry count |
| `EXTRACT_CUTOFF_DAYS` | No | `30` | Days of history to extract; initial runs backfill this window, steady-state runs only pull new listings |
| `AIRFLOW__SMTP__SMTP_HOST` | Yes | `smtp.resend.com` | Production SMTP relay host |
| `AIRFLOW__SMTP__SMTP_PORT` | Yes | `587` | Production SMTP port |
| `AIRFLOW__SMTP__SMTP_STARTTLS` | Yes | `True` | SMTP StartTLS flag |
| `AIRFLOW__SMTP__SMTP_SSL` | Yes | `False` | SMTP SSL flag |
| `AIRFLOW__SMTP__SMTP_USER` | Yes | `resend` | SMTP username |
| `AIRFLOW__SMTP__SMTP_PASSWORD` | Yes | *None* | SMTP password / Resend API key |
| `AIRFLOW__SMTP__SMTP_MAIL_FROM` | Yes | *None* | SMTP sender email |
| `SMTP_TO` | Yes | `admin@example.com` | Email recipient for Airflow alerts |

### Service Ports

For production hardening, all services are network isolated within the Docker bridge network. No ports are exposed publicly to the host interface.

For local development, `docker-compose.override.yml` is used to expose ports securely and bind them exclusively to `127.0.0.1`:

| Service | Port | Binding | Purpose |
|---------|------|---------|---------|
| Airflow WebUI | 8080 | `127.0.0.1:8080` | DAG monitoring and triggering |
| PostgreSQL (app) | 5432 | `127.0.0.1:5432` | Korean rental listings database |
| PostgreSQL (Airflow) | 5433 | `127.0.0.1:5433` | Airflow metadata database |
| Redis | 6379 | `127.0.0.1:6379` | Deduplication cache |
| MailHog SMTP | 1025 | `127.0.0.1:1025` | Email relay (dev only, under `dev` profile) |
| MailHog WebUI | 8025 | `127.0.0.1:8025` | Email inbox viewer (dev only, under `dev` profile) |

### Deploying

```bash
# Build and start all services
docker compose up -d --build

# Verify services are running
docker compose ps

# Check service health
docker compose ps --filter "health=healthy"
```

The `airflow-init` service runs migrations and creates the admin user automatically. Wait ~30 seconds for all services to become healthy.

### Coolify Deployment

When deploying to a production host managed by **Coolify**:

1. **Environment Variables**: Configure the following environment variables in the Coolify project/application Environment variables tab:
   - `POSTGRES_PASSWORD`: A unique cryptographically strong password. Do not commit this.
   - `AIRFLOW_DB_PASSWORD`: A unique strong password for the Airflow metadata database.
   - `AIRFLOW_ADMIN_PASSWORD`: A strong password to log into the Airflow WebUI.
   - `AIRFLOW_HOST`: The domain you plan to route the Airflow WebUI through (e.g. `airflow.example.com`).
   - `SMTP_PASSWORD`: A fresh API key generated from the **Resend** SMTP dashboard (see network isolation and SMTP setup below). Note: Any previously exposed SMTP/Resend API keys (e.g. leaked in chat) are compromised and MUST be rotated.
2. **Encrypted Storage**: Coolify automatically encrypts environment variables stored in its database.
3. **Fail-Fast behavior**: If any of the required passwords above are missing or empty, database configuration will raise a `RuntimeError` immediately upon start.
4. **Postgres Backups & Disaster Recovery**: Production database backups are managed automatically by Coolify. See the comprehensive [backups.md](docs/backups.md) for automated scheduling, offsite copy setups, manual recovery tools, and restore drill instructions.

### Verifying the Deployment

```bash
# Run the smoke test
make verify-deploy
```

This target:
1. Brings down and removes volumes (fresh start)
2. Builds and starts the full stack
3. Waits for services to become healthy
4. Verifies the `korean-rental-etl` package is installed in the Airflow container
5. Verifies the CLI is on PATH inside the container
6. Verifies all DAGs import without errors

### Triggering DAGs

**Via Airflow WebUI:**
1. Open http://localhost:8080
2. Log in with admin / `AIRFLOW_ADMIN_PASSWORD`
3. Find `korean_rental_full_etl` or `korean_rental_cleanup` in the DAG list
4. Click the DAG name, then click the play icon to trigger

**Via CLI:**
```bash
# Run the full ETL pipeline once
docker compose exec airflow-scheduler korean-rental-etl run-all

# Or run individual steps
docker compose exec airflow-scheduler korean-rental-etl extract --all
docker compose exec airflow-scheduler korean-rental-etl transform --all
docker compose exec airflow-scheduler korean-rental-etl load
docker compose exec airflow-scheduler korean-rental-etl validate --run-id <run-id>
```

### Viewing Logs

**Airflow task logs:**
```bash
# Stream logs from the scheduler
docker compose logs -f airflow-scheduler

# Stream logs from the webserver
docker compose logs -f airflow-webserver

# View task logs in the WebUI: DAG → Task Instance → Logs tab
```

**Application logs:**
```bash
# Logs are written to the airflow_logs named volume
# Access via: docker compose exec airflow-scheduler tail -f /opt/airflow/logs/<dag_id>/<task_id>/<run_id>/attempt-1.log
```

### Troubleshooting

**Port already in use:**
```bash
# Find which process is using the port (e.g., 8080)
lsof -i :8080
# Kill it or change the port in docker-compose.yml
```

**airflow-init fails or hangs:**
```bash
# Check the init logs
docker compose logs airflow-init

# If it's stuck, restart it
docker compose restart airflow-init

# Verify the Airflow metadata DB is healthy
docker compose exec airflow_postgres pg_isready -U airflow
```

**DAG import errors:**
```bash
# Check for syntax errors in DAG files
docker compose exec airflow-scheduler python -m py_compile /opt/airflow/dags/*.py

# View the full DAG bag report
docker compose exec airflow-scheduler python -c "from airflow.models import DagBag; db = DagBag(include_examples=False); print(db.import_errors)"
```

**PostgreSQL healthcheck failing:**
```bash
# Verify the password is correct in .env
docker compose exec postgres psql -U etl_user -d korean_rental -c "SELECT 1"

# Check Postgres logs
docker compose logs postgres
```

**Redis connection refused:**
```bash
# Verify Redis is running
docker compose exec redis redis-cli ping

# Check Redis logs
docker compose logs redis
```

### Production Hardening Posture

This pipeline is fully hardened for production environments:

- **Network Isolation**: By default, `docker-compose.yml` does not expose any ports to the host interface. All inter-service communication happens securely inside the private Docker network.
- **Local Dev Binding**: Local development uses `docker-compose.override.yml` to safely bind ports to `127.0.0.1`.
- **Secrets Validation**: The database and application will crash immediately on startup if key secret variables (like `POSTGRES_PASSWORD`, `AIRFLOW_DB_PASSWORD`, `AIRFLOW_ADMIN_PASSWORD`) are unset or empty.
- **Coolify Integration**: Traefik labels are preconfigured for the `airflow-webserver` to allow Coolify to automatically provision Let's Encrypt TLS certificates and manage secure routing via the domain specified in `AIRFLOW_HOST`.
- **Resend SMTP**: Production notification utilizes Resend SMTP over TLS/StartTLS, ensuring robust delivery of success/failure alerts.

## Developer's Guide

### Local Setup

```bash
# Install dependencies with dev and test extras
make dev

# Or manually with uv
uv sync --extra dev --extra test
```

### Make Targets

| Target | Purpose |
|--------|---------|
| `make help` | Show all available targets |
| `make install` | Install project dependencies |
| `make dev` | Install with dev and test extras |
| `make lint` | Run ruff linter and formatter check |
| `make format` | Auto-format code with ruff |
| `make typecheck` | Run mypy type checker |
| `make test` | Run unit tests with coverage (80% gate on transform module) |
| `make test-integration` | Run integration tests (requires Docker Compose) |
| `make ci` | Run full CI pipeline (lint + typecheck + test) |
| `make smoke` | Run smoke tests (DAG imports + CLI version) |
| `make verify-deploy` | Verify production-ready containerized deployment |
| `make backup` | Create a timestamped Postgres custom-format dump under `backups/` |
| `make restore` | Restore from a backup: `make restore BACKUP_FILE=backups/<file>.dump` |
| `make clean` | Clean build artifacts and caches |

### Project Structure

```
src/korean_rental_etl/
├── cli/
│   └── cli.py                 # Click CLI entry point
├── extract/
│   ├── base_scraper.py        # Abstract scraper base class
│   ├── scraper_factory.py     # Scraper instantiation
│   ├── scrapers/              # Concrete scraper implementations
│   │   ├── svkoreans.py
│   │   ├── gtksa.py
│   │   ├── missyusa.py
│   │   ├── ktown_koreadaily.py
│   │   ├── radiokorea.py
│   │   └── illinoisksa.py
│   ├── raw_writer.py          # Write raw HTML to raw.scraped_pages
│   └── source_config.py       # Load sources from config/sources.yml
├── transform/
│   ├── pipeline.py            # Main transform orchestration
│   ├── parsers/               # HTML parsers per source
│   ├── normalizers/           # Korean text normalization
│   ├── dedup/                 # Fuzzy + hash deduplication
│   └── staging_writer.py      # Write to staging.listings_staging
├── load/
│   ├── upserter.py            # Upsert staging → public.listings
│   ├── cleanup.py             # Mark stale, purge old pages
│   └── audit.py               # Audit trail logging
├── validation/
│   └── thresholds.py          # Validation rules and checks
├── db/
│   ├── connection.py          # PostgreSQL connection pool
│   └── models.py              # SQLAlchemy ORM models
└── text_utils.py              # Korean text utilities

tests/
├── unit/                      # Unit tests (no external services)
│   ├── cli/
│   ├── extract/
│   ├── transform/
│   ├── load/
│   └── validation/
└── integration/               # Integration tests (requires Docker)
    ├── full_etl_dag/
    ├── load/
    └── db/

airflow/
└── dags/
    ├── full_etl.py            # 6-hour ETL pipeline
    └── cleanup.py             # Daily cleanup tasks

sql/
└── migrations/
    ├── 001_initial_schema.sql # Core schema + sources seed
    ├── 002_fix_fts_index.sql  # FTS index NULL handling fix
    └── 003_add_illinoisksa.sql # Add illinoisksa.org/housing source
```

### Running Tests

**Unit tests (fast, no Docker required):**
```bash
make test
```

**Integration tests (requires Docker Compose):**
```bash
make test-integration
```

**Full CI (lint + typecheck + unit tests):**
```bash
make ci
```

Note: The coverage gate requires 80% coverage on the `transform` module. Pre-existing mypy errors in `transform/` and `extract/` are known and out of scope for this release.

### CLI Command Reference

| Command | Flags | Purpose |
|---------|-------|---------|
| `korean-rental-etl sources list` | — | List all configured sources |
| `korean-rental-etl sources show <name>` | — | Show details for a source |
| `korean-rental-etl extract` | `--source <name>` or `--all`, `--dag-id`, `--run-id` | Extract listings from sources |
| `korean-rental-etl transform` | `--source <name>` or `--all`, `--limit N`, `--dag-id`, `--run-id` | Transform extracted listings |
| `korean-rental-etl load` | `--source <name>`, `--dag-id`, `--run-id` | Load transformed listings |
| `korean-rental-etl validate` | `--run-id <id>` | Validate loaded listings |
| `korean-rental-etl run-all` | `--dag-id`, `--run-id` | Run full pipeline (extract → transform → load → validate) |
| `korean-rental-etl cleanup mark-stale` | `--days N` | Mark listings inactive if not seen in N days |
| `korean-rental-etl cleanup purge-pages` | `--days N` | Delete raw HTML pages older than N days |

### Adding a New Source

1. **Add source to `config/sources.yml`:**
   ```yaml
   - name: newsource
     display_name: New Source
     base_url: https://newsource.com/listings
     fetcher_type: StealthyFetcher
     schedule_cron: "0 */6 * * *"
     is_active: true
   ```

2. **Create scraper in `src/korean_rental_etl/extract/scrapers/newsource.py`:**
   ```python
   from korean_rental_etl.extract.base_scraper import BaseScraper
   
   class NewSourceScraper(BaseScraper):
       def crawl_list_pages(self):
           # Yield (url, html_content) tuples
           pass
       
       def fetch_detail(self, url):
           # Return detail page HTML
           pass
   ```

3. **Create parser in `src/korean_rental_etl/transform/parsers/newsource.py`:**
   ```python
   from korean_rental_etl.transform.parsers.base_parser import BaseParser
   
   class NewSourceParser(BaseParser):
       def parse(self, html):
           # Return dict with keys: title_ko, body_ko, raw_price, raw_location, etc.
           pass
   ```

4. **Register in `src/korean_rental_etl/extract/scraper_factory.py`:**
   ```python
   elif source_config.name == "newsource":
       return NewSourceScraper(source_config, source_id)
   ```

5. **Create migration `sql/migrations/NNN_add_newsource.sql`:**
   ```sql
   INSERT INTO public.sources (name, display_name, base_url, fetcher_type, schedule_cron, is_active)
   VALUES ('newsource', 'New Source', 'https://newsource.com/listings', 'StealthyFetcher', '0 */6 * * *', TRUE);
   ```

6. **Write tests in `tests/unit/extract/test_newsource_scraper.py` and `tests/unit/transform/test_newsource_parser.py`.**

### Database Schema

The database uses four schemas that mirror the ETL stages:

```
public  → catalog tables (sources, listings)
raw     → scraped HTML before parsing (scraped_pages)
staging → parsed but not-yet-loaded rows (listings_staging)
audit   → run-level execution logs (etl_runs)
```

**Entity-relationship diagram:**

```mermaid
erDiagram
    sources {
        SERIAL id PK
        VARCHAR name UK "unique source key"
        VARCHAR display_name
        TEXT base_url
        VARCHAR fetcher_type "StealthyFetcher|DynamicFetcher"
        VARCHAR schedule_cron
        BOOLEAN is_active
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }
    scraped_pages {
        BIGSERIAL id PK
        INTEGER source_id FK
        TEXT url
        TEXT html_content
        VARCHAR content_hash "SHA-256, dedup key"
        INTEGER http_status
        TEXT list_page_location "e.g. [LA], [애틀랜타]"
        TIMESTAMPTZ fetched_at
    }
    listings_staging {
        BIGSERIAL id PK
        INTEGER source_id FK
        VARCHAR source_listing_id
        TEXT url
        TEXT title_ko
        TEXT body_ko
        NUMERIC rent_monthly_usd
        NUMERIC deposit_usd
        VARCHAR lease_type "monthly|jeonse|short_term|lease"
        TIMESTAMPTZ posted_at_utc
        VARCHAR city
        TEXT address_raw
        VARCHAR phone
        VARCHAR kakao_id
        VARCHAR category
        GEOMETRY geo_point "PostGIS Point(4326)"
        BOOLEAN is_duplicate
        BIGINT duplicate_of "→ listings_staging.id"
        BIGINT canonical_id "→ listings.id"
        TIMESTAMPTZ parsed_at
        TIMESTAMPTZ loaded_at "NULL until upsert"
        JSONB errors
    }
    listings {
        BIGSERIAL id PK
        INTEGER source_id FK
        VARCHAR source_listing_id
        TEXT url
        TEXT title_ko
        TEXT body_ko
        NUMERIC rent_monthly_usd
        NUMERIC deposit_usd
        VARCHAR lease_type
        TIMESTAMPTZ posted_at_utc
        TIMESTAMPTZ first_seen_at
        TIMESTAMPTZ last_seen_at
        VARCHAR city
        TEXT address_raw
        GEOMETRY geo_point
        VARCHAR phone
        VARCHAR category
        BOOLEAN is_canonical
        INTEGER duplicate_count
        BOOLEAN is_active "false = stale"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }
    etl_runs {
        BIGSERIAL id PK
        VARCHAR dag_id "Airflow DAG"
        VARCHAR task_id "extract|transform|load"
        VARCHAR run_id "Airflow run_id"
        VARCHAR source_name "→ sources.name (by value)"
        VARCHAR status "running|success|failed"
        INTEGER rows_extracted
        INTEGER rows_transformed
        INTEGER rows_loaded
        INTEGER rows_failed
        TEXT error_message
        TIMESTAMPTZ started_at
        TIMESTAMPTZ finished_at
        NUMERIC duration_sec
    }

    sources        ||--o{ scraped_pages    : "scraped from"
    sources        ||--o{ listings_staging : "parsed for"
    sources        ||--o{ listings         : "published to"
    scraped_pages  }o..o{ listings_staging : "parsed into (by url+hash)"
    listings_staging }o..o| listings       : "upserted to (canonical_id)"
```

**Tables at a glance:**

| Schema | Table | Role | Unique key |
|--------|-------|------|------------|
| `public` | `sources` | Source registry | `name` |
| `raw` | `scraped_pages` | Raw HTML history | `(source_id, url, content_hash)` |
| `staging` | `listings_staging` | Parsed rows pending load | `(source_id, source_listing_id)` |
| `public` | `listings` | Canonical clean listings | `(source_id, source_listing_id)` |
| `audit` | `etl_runs` | Per-task execution audit | `id` (looked up via `run_id`) |

**Data flow through the tables:**

1. **Extract** writes one row per fetched page into `raw.scraped_pages` (hashes prevent re-storing identical HTML).
2. **Transform** reads unparsed rows from `raw.scraped_pages`, parses them, and writes to `staging.listings_staging` with `parsed_at` set and `loaded_at = NULL`.
3. **Load** upserts `staging.listings_staging` rows into `public.listings` keyed on `(source_id, source_listing_id)`, then sets `loaded_at = NOW()` to mark idempotent completion.
4. **Validate** reads `audit.etl_runs` and `staging.listings_staging` for the run, applies threshold checks (null rate, parsed-row count, FK integrity), and records pass/fail.
5. **Cleanup** flips `listings.is_active = false` for rows whose `last_seen_at` is older than N days, and deletes `raw.scraped_pages` rows older than M days.

**Key indexes:**

| Index | Definition | Used for |
|-------|------------|----------|
| `idx_listings_korean_fts` | `GIN ((COALESCE(title_ko,'') \|\| ' ' \|\| COALESCE(body_ko,'') \|\| ' ' \|\| COALESCE(address_raw,'')) gin_trgm_ops)` | Korean trigram full-text search (NULL-safe via migration 002) |
| `idx_listings_geo_point` | `GIST (geo_point)` | Spatial queries (within radius, bounding box) |
| `idx_listings_source_id` / `_city` / `_category` / `_is_active` / `_posted_at` / `_last_seen` | B-tree on each | Common filter columns |
| `idx_scraped_pages_source_url` | B-tree `(source_id, url)` | Lookup by source + URL |
| `idx_staging_source_listing` | UNIQUE B-tree `(source_id, source_listing_id)` | Upsert lookup |
| `idx_etl_runs_run_id` | B-tree `(run_id)` | Resolve Airflow `run_id` → numeric audit id |

**PostgreSQL extensions:** `postgis` (for `GEOMETRY` and GiST), `pg_trgm` (for trigram FTS).

The full schema definitions live in [`sql/migrations/001_initial_schema.sql`](sql/migrations/001_initial_schema.sql) and [`sql/migrations/002_fix_fts_index.sql`](sql/migrations/002_fix_fts_index.sql).

### Migrations

Migrations are SQL files in `sql/migrations/` with numeric prefixes (e.g., `001_initial_schema.sql`, `002_fix_fts_index.sql`). They are applied automatically when the PostgreSQL container starts via the `docker-entrypoint-initdb.d` mechanism. To add a new migration:

1. Create `sql/migrations/NNN_description.sql` (increment NNN)
2. Write idempotent SQL (use `IF NOT EXISTS`, `ON CONFLICT`, etc.)
3. Commit and push
4. On next `docker compose up`, the migration runs automatically

For existing databases, manually run the migration:
```bash
docker compose exec postgres psql -U etl_user -d korean_rental -f /docker-entrypoint-initdb.d/NNN_description.sql
```

## DAG Schedules

| DAG | Schedule | Tasks |
|-----|----------|-------|
| `korean_rental_full_etl` | Every 6 hours (0 */6 * * *) | health_check → extract → transform → load → validate → notify |
| `korean_rental_cleanup` | Daily at 03:00 UTC (0 3 * * *) | mark_stale_listings_inactive → purge_old_raw_pages |

## License

MIT

# Korean Rental ETL

![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%20%2B%20PostGIS-336791)
![Redis](https://img.shields.io/badge/Redis-7-DC382D)
![Scheduler](https://img.shields.io/badge/scheduler-Supercronic-lightweight)

ETL pipeline that scrapes Korean-American rental boards, normalizes listings, and loads them into PostgreSQL.

## Architecture

```text
Supercronic (6-hour schedule)
  -> source preflight
  -> extract (all active sources)
  -> transform
  -> load
  -> validate

Daily cleanup
  -> mark listings stale after 14 days
  -> purge raw pages after 90 days
```

The lightweight `etl-runner` preserves the former Airflow workflow's task order, schedules, retries, timeouts, `dag_id`/`run_id` audit values, validation, persistent run history, task logs, overlap prevention, and optional SMTP notifications. It removes the Airflow webserver, scheduler, metadata PostgreSQL database, initialization container, and Airflow Python dependency.

Business output is unchanged:

```text
source sites -> raw.scraped_pages -> staging.listings_staging -> public.listings
                                  -> audit.etl_runs
```

## Sources

| Name | URL | Status |
|---|---|---|
| svkoreans | https://svkoreans.com/rent_housing | Active |
| gtksa | https://gtksa.net/bbs/board.php?bo_table=rent | Active |
| missyusa | https://missyusa.com/town9 | Active |
| ktown_koreadaily | https://ktown.koreadaily.com/ad_rent/rentlist | Active |
| radiokorea | https://m.radiokorea.com/c_realestate | Active |
| illinoisksa | https://illinoisksa.org/housing | Active |
| hanintown | https://hanintown.com | Disabled |

## Quick start

```bash
cp .env.example .env
# Set POSTGRES_PASSWORD in .env
docker compose up -d --build
docker compose ps
```

The stack contains four services:

- `postgres`: application database
- `redis`: scraper cache and deduplication
- `app-migrate`: one-shot idempotent SQL migration job
- `scheduler`: Supercronic plus the Python ETL and workflow runner

No service exposes a host port by default.

## Operate

### Run workflows manually

```bash
# Same full ETL sequence as the scheduled 6-hour run
docker compose exec scheduler etl-runner run korean_rental_full_etl

# Daily cleanup sequence
docker compose exec scheduler etl-runner run korean_rental_cleanup
```

### Inspect status, history, and logs

```bash
docker compose exec scheduler etl-runner status
docker compose exec scheduler etl-runner history --limit 20
docker compose logs -f scheduler
```

Per-workflow logs and JSONL history persist in named volumes:

- `/var/log/korean-rental-etl`
- `/var/lib/korean-rental-etl/history.jsonl`

Only one workflow can run at a time. A second overlapping invocation exits with code `75` instead of duplicating ETL work.

### Schedules

| Workflow | Cron (UTC) | Retries | Behavior |
|---|---:|---:|---|
| `korean_rental_full_etl` | `0 */6 * * *` | 1 | preflight → extract → transform → load → validate |
| `korean_rental_cleanup` | `0 3 * * *` | 2 | mark stale → purge raw pages |

Schedules live in `scheduler/crontab`; workflow definitions live in `src/korean_rental_etl/scheduler/runner.py`.

### Notifications

Notifications are disabled unless both `SMTP_TO` and `SMTP_HOST` are set. Supported variables:

```dotenv
SMTP_TO=admin@example.com
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_STARTTLS=true
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=ETL Alerts <alerts@example.com>
```

### Individual ETL commands

```bash
docker compose exec scheduler korean-rental-etl sources check
docker compose exec scheduler korean-rental-etl extract --all
docker compose exec scheduler korean-rental-etl transform --all
docker compose exec scheduler korean-rental-etl load
docker compose exec scheduler korean-rental-etl validate --run-id <run-id>
```

## Configuration

| Variable | Required | Default | Purpose |
|---|---:|---|---|
| `POSTGRES_PASSWORD` | Yes | — | Application database password |
| `POSTGRES_DB` | No | `korean_rental` | Database name |
| `POSTGRES_USER` | No | `etl_user` | Database user |
| `NOMINATIM_USER_AGENT` | No | project default | Geocoder identification |
| `NOMINATIM_RATE_LIMIT_PER_SEC` | No | `1` | Geocoder request rate |
| `DOWNLOAD_DELAY_SEC` | No | `2.0` | Delay between scraper requests |
| `CONCURRENT_REQUESTS` | No | `2` | Scraper concurrency |
| `MAX_RETRIES` | No | `3` | Scraper retry count |
| `EXTRACT_CUTOFF_DAYS` | No | `30` | Listing history window |

See `.env.example` for the complete list. Airflow-specific passwords, hostnames, and SMTP names are no longer used.

## Development

```bash
make dev
make lint
make typecheck
make test
make smoke
```

Integration tests require the test database stack:

```bash
docker compose -f docker-compose.test.yml down -v
docker compose -f docker-compose.test.yml up -d --wait
uv run --extra test pytest tests/integration -m integration
```

To verify the production image and scheduler:

```bash
POSTGRES_PASSWORD='replace-me' make verify-deploy
```

## Project layout

| Area | Path |
|---|---|
| Extract | `src/korean_rental_etl/extract/` |
| Transform | `src/korean_rental_etl/transform/` |
| Load | `src/korean_rental_etl/load/` |
| Validation | `src/korean_rental_etl/validation/` |
| Scheduler | `src/korean_rental_etl/scheduler/` and `scheduler/crontab` |
| Database | `sql/migrations/` |
| Infrastructure | `Dockerfile`, `docker-compose.yml` |
| Tests | `tests/` |

Database backup and recovery instructions are in [`docs/backups.md`](docs/backups.md).

## License

MIT

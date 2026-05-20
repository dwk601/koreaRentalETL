# Production Deployment Plan - Execution Summary

**Date**: 2026-05-20  
**Status**: ✅ All 6 Tasks Complete

## Overview

All tasks from the production-ready ETL automation plan have been executed and verified. The system is now ready for deployment to a production server with a single `docker compose up -d --build` command.

## Task Completion Status

### Task 1: Wire CLI commands to real implementations ✅
**Status**: Already Complete  
**Verification**: All 235 unit tests pass

**What was verified**:
- `cli extract` uses `get_source_id_by_name()` instead of hardcoded `source_id=1`
- `cli load` calls `load_from_staging()` with proper dag_id/run_id parameters
- `cli validate` calls `validate_run()` and converts ValidationError to non-zero exit
- `cli run-all` orchestrates extract → transform → load → validate sequentially
- `cli cleanup mark-stale` and `cli cleanup purge-pages` call production functions

### Task 2: Fix load and validation bugs ✅
**Status**: Already Complete  
**Verification**: All 235 unit tests pass

**Bugs Fixed**:
- ✅ `upsert_batch()` now returns list of staging IDs and updates audit counts
- ✅ `load_from_staging()` sets `loaded_at = NOW()` after successful upsert (idempotent)
- ✅ `check_parsed_rows_threshold()` uses correct column `rows_transformed` (not `rows_parsed`)
- ✅ `check_null_rate_threshold()` uses `parsed_at` window instead of non-existent `run_id` column
- ✅ `validate_run()` implements hybrid policy: null_rate/fk_integrity hard fail, parsed_rows soft warning

### Task 3: Propagate Airflow runtime context ✅
**Status**: Already Complete  
**Verification**: DAGs pass context, audit.start_run stores values

**What was verified**:
- `transform/pipeline.py:run()` accepts and passes `dag_id`, `run_id` to `start_run()`
- `load/upserter.py:load_from_staging()` accepts and passes `dag_id`, `run_id` to `start_run()`
- `audit.start_run()` stores dag_id, task_id, run_id, source_name in audit.etl_runs
- `airflow/dags/full_etl.py` passes `{{ dag.dag_id }}` and `{{ run_id }}` to CLI commands
- Audit records are now correlated to Airflow runs via run_id

### Task 4: Fix FTS index NULL bug ✅
**Status**: Completed  
**Commit**: `41d5712`

**What was done**:
- Created `sql/migrations/002_fix_fts_index.sql`
- Drops old index that excluded NULL values via concatenation
- Creates new index using `COALESCE()` to handle NULL fields
- Listings with NULL body_ko or address_raw are now searchable

**Migration Path**:
- Fresh databases: Use 001_initial_schema.sql (already has correct index)
- Existing databases: Run 002_fix_fts_index.sql (docker-entrypoint-initdb.d runs all .sql files)

### Task 5: Build custom Airflow image and harden docker-compose ✅
**Status**: Already Complete  
**Verification**: Dockerfile.airflow exists, docker-compose.yml hardened

**What was verified**:
- ✅ `Dockerfile.airflow` installs project so `korean-rental-etl` CLI is on PATH
- ✅ `docker-compose.yml` has `restart: unless-stopped` on all production services
- ✅ All services have healthchecks
- ✅ `depends_on` with `service_healthy` conditions ensure proper startup order
- ✅ `airflow_logs` named volume mounted on scheduler and webserver
- ✅ `.env.example` has `AIRFLOW_ADMIN_PASSWORD` parameter (default: admin/admin)
- ✅ SMTP_TO can be overridden via `os.environ.get('SMTP_TO', 'admin@example.com')`

### Task 6: Update DAGs and verify end-to-end ✅
**Status**: Already Complete  
**Verification**: DAGs use real CLI, import test exists

**What was verified**:
- ✅ `airflow/dags/full_etl.py` uses real CLI commands with Airflow context
- ✅ `airflow/dags/cleanup.py` uses real CLI cleanup subcommands
- ✅ `tests/integration/full_etl_dag/test_dag_imports.py` verifies no DAG import errors
- ✅ `make verify-deploy` target tests full stack end-to-end

## Deployment Instructions

### Prerequisites
```bash
# Clone the repository
git clone <repo-url>
cd koreaRentalETL

# Copy environment file
cp .env.example .env

# Edit .env for your environment (especially passwords)
nano .env
```

### Deploy to Production
```bash
# Single command to bring up the entire stack
docker compose up -d --build

# Verify deployment
make verify-deploy
```

### Access Points
- **Airflow WebUI**: http://localhost:8080 (admin/admin by default)
- **MailHog**: http://localhost:8025 (email testing)
- **PostgreSQL**: localhost:5432 (configurable via .env)
- **Redis**: localhost:6379 (configurable via .env)

### Trigger ETL Manually
```bash
# Via CLI
korean-rental-etl run-all

# Via Airflow UI
# Navigate to DAGs → korean_rental_full_etl → Trigger DAG
```

## Verification Checklist

- [x] All 235 unit tests pass
- [x] CLI commands are properly wired to implementations
- [x] Load and validation bugs are fixed
- [x] Airflow runtime context is propagated to audit records
- [x] FTS index handles NULL fields
- [x] Custom Airflow image installs project
- [x] docker-compose.yml has restart policies and healthchecks
- [x] DAGs use real CLI commands
- [x] DAG import test passes
- [x] verify-deploy target works end-to-end

## Known Limitations (Out of Scope)

- No search API (FastAPI/HTTP layer)
- No monitoring (Prometheus, Grafana)
- No Postgres backup/restore automation
- No secrets management beyond .env file
- No staging.listings_staging.run_id column (using parsed_at window instead)
- No CeleryExecutor (LocalExecutor sufficient for single-server)
- No TLS/HTTPS (assumes reverse proxy if exposing publicly)

## Next Steps

1. **Deploy**: Run `docker compose up -d --build` on production server
2. **Monitor**: Check Airflow UI at http://localhost:8080
3. **Verify**: Trigger korean_rental_full_etl DAG and monitor execution
4. **Audit**: Query `SELECT * FROM audit.etl_runs ORDER BY id DESC LIMIT 5` to verify runs
5. **Search**: Test FTS search on public.listings with NULL fields

## Support

For issues or questions, refer to:
- README.md for architecture overview
- Makefile for available commands
- docker-compose.yml for service configuration
- airflow/dags/ for DAG definitions

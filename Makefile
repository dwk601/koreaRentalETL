.PHONY: help lint typecheck test test-integration ci smoke clean install dev backup restore

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install project dependencies
	uv sync

dev: ## Install with dev dependencies
	uv sync --extra dev --extra test

lint: ## Run ruff linter and formatter check
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

format: ## Auto-format code with ruff
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

typecheck: ## Run mypy type checker
	uv run mypy src/

test: ## Run unit tests with coverage
	uv run pytest tests/unit/ -v --cov=korean_rental_etl.transform --cov-report=term-missing --cov-fail-under=80

test-integration: ## Run integration tests (requires Docker Compose)
	uv run pytest tests/integration/ -v -m integration

ci: lint typecheck test ## Run full CI pipeline (lint + typecheck + test)

smoke: ## Run scheduler and CLI smoke tests
	uv run korean-rental-etl --version
	uv run etl-runner healthcheck
	uv run etl-runner workflows >/dev/null
	@echo "Smoke test passed"

verify-deploy: ## Build and verify the lightweight scheduler container
	docker compose up -d --build
	@echo "Waiting for scheduler health..."
	@for i in $$(seq 1 60); do \
		status=$$(docker inspect --format='{{.State.Health.Status}}' korean_rental_scheduler 2>/dev/null || true); \
		[ "$$status" = healthy ] && break; \
		[ "$$i" = 60 ] && { docker compose ps; exit 1; }; \
		sleep 2; \
	done
	docker compose exec -T scheduler korean-rental-etl --version
	docker compose exec -T scheduler etl-runner healthcheck
	docker compose exec -T scheduler etl-runner workflows >/dev/null
	@echo "Lightweight scheduler verified"

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

backup: ## Generate a timestamped Postgres custom-format backup (.dump)
	@mkdir -p backups
	docker compose exec -T postgres sh -c 'PGPASSWORD=$$POSTGRES_PASSWORD pg_dump -U $$POSTGRES_USER -d $$POSTGRES_DB -Fc' > backups/korean_rental_$$(date +%Y-%m-%dT%H-%M-%S).dump
	@echo "Backup completed successfully!"

restore: ## Restore the Postgres database from a backup file (e.g. make restore BACKUP_FILE=backups/file.dump)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "ERROR: BACKUP_FILE is required. Example: make restore BACKUP_FILE=backups/korean_rental_xyz.dump"; \
		exit 1; \
	fi
	docker compose exec -T postgres sh -c 'PGPASSWORD=$$POSTGRES_PASSWORD pg_restore -U $$POSTGRES_USER -d $$POSTGRES_DB --clean --if-exists -Fc' < $(BACKUP_FILE)
	@echo "Restore completed successfully!"

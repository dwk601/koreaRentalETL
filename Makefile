.PHONY: help lint typecheck test test-integration ci smoke clean install dev

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

smoke: ## Run smoke tests (DAG imports + basic CLI)
	uv run python -m korean_rental_etl.cli --version
	@echo "Smoke test passed"

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

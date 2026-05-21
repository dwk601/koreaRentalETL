"""Unit tests for new and modified CLI commands."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from korean_rental_etl.cli.cli import main
from korean_rental_etl.validation.thresholds import ValidationError


class TestCliCommands:
    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_extract_calls_scraper_extract(self, runner: CliRunner) -> None:
        with (
            patch("korean_rental_etl.transform.pipeline.get_source_id_by_name") as mock_get_id,
            patch("korean_rental_etl.extract.scraper_factory.ScraperFactory.create") as mock_create,
        ):
            mock_get_id.return_value = 42
            mock_scraper = mock_create.return_value
            mock_scraper.extract.return_value = (10, 2)

            result = runner.invoke(
                main,
                ["extract", "--source", "svkoreans", "--dag-id", "dag123", "--run-id", "run123"],
            )

            assert result.exit_code == 0
            assert "Extracted 10 listings" in result.output
            mock_get_id.assert_called_once_with("svkoreans")
            mock_scraper.extract.assert_called_once_with(dag_id="dag123", run_id="run123")

    def test_load_calls_load_from_staging(self, runner: CliRunner) -> None:
        with (
            patch("korean_rental_etl.transform.pipeline.get_source_id_by_name") as mock_get_id,
            patch("korean_rental_etl.load.upserter.load_from_staging") as mock_load,
        ):
            mock_get_id.return_value = 42
            mock_load.return_value = (5, 0)

            result = runner.invoke(
                main, ["load", "--source", "svkoreans", "--dag-id", "dag123", "--run-id", "run123"]
            )

            assert result.exit_code == 0
            assert "Loaded 5 listings" in result.output
            mock_load.assert_called_once_with(source_id=42, dag_id="dag123", run_id="run123")

    def test_validate_calls_validate_run(self, runner: CliRunner) -> None:
        with (
            patch(
                "korean_rental_etl.validation.thresholds.get_audit_run_id_by_airflow_run_id"
            ) as mock_resolve,
            patch("korean_rental_etl.validation.thresholds.validate_run") as mock_validate,
        ):
            mock_resolve.return_value = 101
            mock_validate.return_value = {
                "run_id": 101,
                "checks": [{"name": "null_rate", "passed": True, "message": "all good"}],
                "passed": True,
            }

            result = runner.invoke(main, ["validate", "--run-id", "run123"])

            assert result.exit_code == 0
            assert "Validation passed!" in result.output
            mock_resolve.assert_called_once_with("run123", task_id="transform")
            mock_validate.assert_called_once_with(101)

    def test_validate_handles_validation_error(self, runner: CliRunner) -> None:
        with (
            patch(
                "korean_rental_etl.validation.thresholds.get_audit_run_id_by_airflow_run_id"
            ) as mock_resolve,
            patch("korean_rental_etl.validation.thresholds.validate_run") as mock_validate,
        ):
            mock_resolve.return_value = 101
            mock_validate.side_effect = ValidationError("Hard constraints failed")

            result = runner.invoke(main, ["validate", "--run-id", "run123"])

            assert result.exit_code == 1
            assert "Validation failed" in result.output

    def test_cleanup_mark_stale(self, runner: CliRunner) -> None:
        with patch("korean_rental_etl.load.cleanup.mark_stale_listings_inactive") as mock_mark:
            mock_mark.return_value = 7

            result = runner.invoke(main, ["cleanup", "mark-stale", "--days", "10"])

            assert result.exit_code == 0
            assert "Marked 7 listings as inactive" in result.output
            mock_mark.assert_called_once_with(days=10)

    def test_cleanup_purge_pages(self, runner: CliRunner) -> None:
        with patch("korean_rental_etl.load.cleanup.purge_old_raw_pages") as mock_purge:
            mock_purge.return_value = 25

            result = runner.invoke(main, ["cleanup", "purge-pages", "--days", "30"])

            assert result.exit_code == 0
            assert "Purged 25 raw pages" in result.output
            mock_purge.assert_called_once_with(days=30)

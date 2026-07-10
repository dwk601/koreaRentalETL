"""Tests for CLI commands."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from korean_rental_etl.cli.cli import main


class TestSourcesCommands:
    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_sources_list(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["sources", "list"])
        assert result.exit_code == 0
        assert "svkoreans" in result.output
        assert "gtksa" in result.output
        assert "missyusa" in result.output
        assert "ktown_koreadaily" in result.output
        assert "radiokorea" in result.output

    def test_sources_show_valid(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["sources", "show", "svkoreans"])
        assert result.exit_code == 0
        assert "svkoreans" in result.output
        assert "svkoreans.com" in result.output

    def test_sources_show_invalid(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["sources", "show", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_sources_check_passes_when_registries_align(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("korean_rental_etl.cli.cli.source_registry_errors", lambda: [])
        result = runner.invoke(main, ["sources", "check"])
        assert result.exit_code == 0
        assert "aligned" in result.output.lower()

    def test_sources_check_fails_with_concise_errors(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "korean_rental_etl.cli.cli.source_registry_errors",
            lambda: ["missing from database: illinoisksa"],
        )
        result = runner.invoke(main, ["sources", "check"])
        assert result.exit_code == 1
        assert "missing from database: illinoisksa" in result.output


class TestExtractCommand:
    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_extract_no_args(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["extract"])
        assert result.exit_code == 1
        assert "specify" in result.output.lower()

    def test_extract_invalid_source(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["extract", "--source", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_extract_all_stops_before_scraping_when_preflight_fails(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "korean_rental_etl.cli.cli.source_registry_errors",
            lambda: ["missing from database: illinoisksa"],
        )
        result = runner.invoke(main, ["extract", "--all"])
        assert result.exit_code == 1
        assert "preflight failed" in result.output.lower()
        assert "missing from database: illinoisksa" in result.output

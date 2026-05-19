"""Tests for CLI commands."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from korean_rental_etl.cli.cli import main, sources_list, sources_show


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

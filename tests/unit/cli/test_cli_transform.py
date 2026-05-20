"""Tests for CLI transform command."""

from unittest.mock import patch

from click.testing import CliRunner

from korean_rental_etl.cli.cli import main


class TestCliTransform:
    """Test CLI transform command."""

    def test_transform_single_source(self):
        """Test transform --source option."""
        runner = CliRunner()

        with patch("korean_rental_etl.transform.pipeline.run") as mock_run:
            mock_run.return_value = (3, 0)

            result = runner.invoke(main, ["transform", "--source", "svkoreans", "--limit", "10"])

            assert result.exit_code == 0
            assert "Transformed 3 listings" in result.output
            mock_run.assert_called_once_with(source_name="svkoreans", limit=10)

    def test_transform_all_sources(self):
        """Test transform --all option."""
        runner = CliRunner()

        with patch("korean_rental_etl.transform.pipeline.run") as mock_run:
            mock_run.return_value = (15, 2)

            result = runner.invoke(main, ["transform", "--all"])

            assert result.exit_code == 0
            assert "Transformed 15 listings" in result.output
            assert "failed 2" in result.output
            mock_run.assert_called_once_with(source_name=None, limit=500)

    def test_transform_neither_source_nor_all(self):
        """Test error when neither --source nor --all is provided."""
        runner = CliRunner()

        result = runner.invoke(main, ["transform"])

        assert result.exit_code == 1
        assert "Please specify --source or --all" in result.output

    def test_transform_with_custom_limit(self):
        """Test transform with custom --limit."""
        runner = CliRunner()

        with patch("korean_rental_etl.transform.pipeline.run") as mock_run:
            mock_run.return_value = (5, 1)

            result = runner.invoke(main, ["transform", "--source", "gtksa", "--limit", "100"])

            assert result.exit_code == 0
            mock_run.assert_called_once_with(source_name="gtksa", limit=100)

    def test_transform_error_handling(self):
        """Test error handling in transform command."""
        runner = CliRunner()

        with patch("korean_rental_etl.transform.pipeline.run") as mock_run:
            mock_run.side_effect = Exception("Database connection failed")

            result = runner.invoke(main, ["transform", "--all"])

            assert result.exit_code == 1
            assert "Error" in result.output

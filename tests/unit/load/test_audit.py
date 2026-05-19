"""Unit tests for audit module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from korean_rental_etl.load.audit import finish_run, start_run


class TestStartRun:
    @patch("korean_rental_etl.load.audit.get_cursor")
    def test_creates_run_record(self, mock_get_cursor: MagicMock) -> None:
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"id": 42}
        mock_get_cursor.return_value = mock_cursor

        run_id = start_run(dag_id="test_dag", task_id="extract", source_name="svkoreans")
        assert run_id == 42
        mock_cursor.execute.assert_called_once()


class TestFinishRun:
    @patch("korean_rental_etl.load.audit.get_cursor")
    def test_updates_run_record(self, mock_get_cursor: MagicMock) -> None:
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"started_at": MagicMock()}
        mock_get_cursor.return_value = mock_cursor

        finish_run(
            run_db_id=42,
            status="success",
            rows_extracted=100,
            rows_transformed=95,
            rows_loaded=90,
        )
        # Two calls: SELECT started_at, UPDATE
        assert mock_cursor.execute.call_count == 2

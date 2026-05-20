"""Unit tests for raw_writer module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from korean_rental_etl.extract.raw_writer import compute_content_hash, save


class TestComputeContentHash:
    def test_deterministic(self) -> None:
        html = "<html><body>test</body></html>"
        h1 = compute_content_hash(html)
        h2 = compute_content_hash(html)
        assert h1 == h2

    def test_different_content_different_hash(self) -> None:
        h1 = compute_content_hash("<html>a</html>")
        h2 = compute_content_hash("<html>b</html>")
        assert h1 != h2

    def test_returns_hex_string(self) -> None:
        h = compute_content_hash("test")
        assert len(h) == 64  # SHA-256 hex digest
        assert all(c in "0123456789abcdef" for c in h)


class TestSave:
    @patch("korean_rental_etl.extract.raw_writer.get_cursor")
    def test_save_inserts_new(self, mock_get_cursor: MagicMock) -> None:
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"id": 1}
        mock_get_cursor.return_value = mock_cursor

        result = save(source_id=1, url="https://example.com", html="<html>test</html>")
        assert result is True
        mock_cursor.execute.assert_called_once()

    @patch("korean_rental_etl.extract.raw_writer.get_cursor")
    def test_save_duplicate_returns_false(self, mock_get_cursor: MagicMock) -> None:
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = None  # ON CONFLICT DO NOTHING
        mock_get_cursor.return_value = mock_cursor

        result = save(source_id=1, url="https://example.com", html="<html>test</html>")
        assert result is False

    @patch("korean_rental_etl.extract.raw_writer.get_cursor")
    def test_save_passes_list_page_location(self, mock_get_cursor: MagicMock) -> None:
        """list_page_location must be persisted as the 6th positional arg."""
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"id": 1}
        mock_get_cursor.return_value = mock_cursor

        save(
            source_id=1,
            url="https://example.com",
            html="<html>test</html>",
            http_status=200,
            list_page_location="LA",
        )
        # Inspect the SQL params
        args, _ = mock_cursor.execute.call_args
        sql, params = args
        assert "list_page_location" in sql
        assert params[-1] == "LA"  # last positional param is list_page_location

    @patch("korean_rental_etl.extract.raw_writer.get_cursor")
    def test_save_list_page_location_defaults_to_none(self, mock_get_cursor: MagicMock) -> None:
        """When omitted, list_page_location is persisted as NULL."""
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"id": 1}
        mock_get_cursor.return_value = mock_cursor

        save(source_id=1, url="https://example.com", html="<html>test</html>")
        args, _ = mock_cursor.execute.call_args
        _, params = args
        assert params[-1] is None

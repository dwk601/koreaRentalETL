"""Unit tests for hash-layer dedup."""

from korean_rental_etl.transform.dedup.hash_layer import should_skip_by_hash


class TestHashLayer:
    """Test content-hash dedup logic."""

    def test_skip_on_existing_hash(self, mocker):
        """Should skip row if content_hash already exists for source."""
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone.return_value = (1,)  # Hash exists
        mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = mocker.MagicMock(return_value=None)
        mocker.patch(
            "korean_rental_etl.transform.dedup.hash_layer.get_cursor", return_value=mock_cursor
        )

        result = should_skip_by_hash(source_id=1, content_hash="abc123")
        assert result is True

    def test_insert_on_new_hash(self, mocker):
        """Should not skip row if content_hash is new."""
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone.return_value = None  # Hash does not exist
        mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = mocker.MagicMock(return_value=None)
        mocker.patch(
            "korean_rental_etl.transform.dedup.hash_layer.get_cursor", return_value=mock_cursor
        )

        result = should_skip_by_hash(source_id=1, content_hash="new_hash")
        assert result is False

    def test_different_source_same_hash(self, mocker):
        """Same hash in different source should not skip."""
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone.return_value = None  # Hash not found for this source
        mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = mocker.MagicMock(return_value=None)
        mocker.patch(
            "korean_rental_etl.transform.dedup.hash_layer.get_cursor", return_value=mock_cursor
        )

        result = should_skip_by_hash(source_id=2, content_hash="abc123")
        assert result is False

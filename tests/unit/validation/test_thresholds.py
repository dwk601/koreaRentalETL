"""Unit tests for validation thresholds."""

from korean_rental_etl.validation.thresholds import (
    check_fk_integrity,
    check_null_rate_threshold,
    check_parsed_rows_threshold,
)


class TestThresholds:
    """Test validation threshold checks."""

    def test_parsed_rows_pass(self, mocker):
        """Should pass when current >= 50% of avg."""
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone.side_effect = [
            {"rows_transformed": 100},
            {"avg_val": 200.0},
        ]  # current=100, avg=200
        mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = mocker.MagicMock(return_value=None)
        mocker.patch("korean_rental_etl.validation.thresholds.get_cursor", return_value=mock_cursor)

        result = check_parsed_rows_threshold(1, threshold_ratio=0.5)
        assert result.passed is True

    def test_parsed_rows_fail(self, mocker):
        """Should fail when current < 50% of avg."""
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone.side_effect = [
            {"rows_transformed": 50},
            {"avg_val": 200.0},
        ]  # current=50, avg=200, threshold=100
        mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = mocker.MagicMock(return_value=None)
        mocker.patch("korean_rental_etl.validation.thresholds.get_cursor", return_value=mock_cursor)

        result = check_parsed_rows_threshold(1, threshold_ratio=0.5)
        assert result.passed is False

    def test_null_rate_pass(self, mocker):
        """Should pass when null_rate <= 20%."""
        mock_cursor = mocker.MagicMock()
        # total=100, null_price=10, null_location=5, null_title=8 -> max=10%
        mock_cursor.fetchone.return_value = {
            "total": 100,
            "null_price": 10,
            "null_location": 5,
            "null_title": 8,
        }
        mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = mocker.MagicMock(return_value=None)
        mocker.patch("korean_rental_etl.validation.thresholds.get_cursor", return_value=mock_cursor)

        result = check_null_rate_threshold(1, max_null_rate=0.20)
        assert result.passed is True

    def test_null_rate_fail(self, mocker):
        """Should fail when null_rate of location or title > 20%."""
        mock_cursor = mocker.MagicMock()
        # total=100, null_price=10, null_location=5, null_title=25 -> max=25%
        mock_cursor.fetchone.return_value = {
            "total": 100,
            "null_price": 10,
            "null_location": 5,
            "null_title": 25,
        }
        mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = mocker.MagicMock(return_value=None)
        mocker.patch("korean_rental_etl.validation.thresholds.get_cursor", return_value=mock_cursor)

        result = check_null_rate_threshold(1, max_null_rate=0.20)
        assert result.passed is False

    def test_null_rate_ignores_rent(self, mocker):
        """Should pass when rent is 100% null but title and location are healthy."""
        mock_cursor = mocker.MagicMock()
        # total=100, null_price=100, null_location=5, null_title=8 -> max=8%
        mock_cursor.fetchone.return_value = {
            "total": 100,
            "null_price": 100,
            "null_location": 5,
            "null_title": 8,
        }
        mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = mocker.MagicMock(return_value=None)
        mocker.patch("korean_rental_etl.validation.thresholds.get_cursor", return_value=mock_cursor)

        result = check_null_rate_threshold(1, max_null_rate=0.20)
        assert result.passed is True

    def test_null_rate_fails_on_missing_title(self, mocker):
        """Should fail when title is missing > 20% even if price is 100% healthy."""
        mock_cursor = mocker.MagicMock()
        # total=100, null_price=0, null_location=5, null_title=25 -> max=25%
        mock_cursor.fetchone.return_value = {
            "total": 100,
            "null_price": 0,
            "null_location": 5,
            "null_title": 25,
        }
        mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = mocker.MagicMock(return_value=None)
        mocker.patch("korean_rental_etl.validation.thresholds.get_cursor", return_value=mock_cursor)

        result = check_null_rate_threshold(1, max_null_rate=0.20)
        assert result.passed is False

    def test_fk_integrity_pass(self, mocker):
        """Should pass when no orphaned rows."""
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone.return_value = {"count": 0}
        mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = mocker.MagicMock(return_value=None)
        mocker.patch("korean_rental_etl.validation.thresholds.get_cursor", return_value=mock_cursor)

        result = check_fk_integrity()
        assert result.passed is True

    def test_fk_integrity_fail(self, mocker):
        """Should fail when orphaned rows exist."""
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone.return_value = {"count": 5}
        mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = mocker.MagicMock(return_value=None)
        mocker.patch("korean_rental_etl.validation.thresholds.get_cursor", return_value=mock_cursor)

        result = check_fk_integrity()
        assert result.passed is False

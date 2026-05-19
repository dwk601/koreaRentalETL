"""Unit tests for validation thresholds."""

import pytest

from korean_rental_etl.validation.thresholds import (
    ThresholdResult,
    ValidationError,
    check_fk_integrity,
    check_null_rate_threshold,
    check_parsed_rows_threshold,
)


class TestThresholds:
    """Test validation threshold checks."""

    def test_parsed_rows_pass(self, mocker):
        """Should pass when current >= 50% of avg."""
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone.side_effect = [(100,), (200.0,)]  # current=100, avg=200
        mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = mocker.MagicMock(return_value=None)
        mocker.patch("korean_rental_etl.validation.thresholds.get_cursor", return_value=mock_cursor)

        result = check_parsed_rows_threshold(1, threshold_ratio=0.5)
        assert result.passed is True

    def test_parsed_rows_fail(self, mocker):
        """Should fail when current < 50% of avg."""
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone.side_effect = [(50,), (200.0,)]  # current=50, avg=200, threshold=100
        mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = mocker.MagicMock(return_value=None)
        mocker.patch("korean_rental_etl.validation.thresholds.get_cursor", return_value=mock_cursor)

        result = check_parsed_rows_threshold(1, threshold_ratio=0.5)
        assert result.passed is False

    def test_null_rate_pass(self, mocker):
        """Should pass when null_rate <= 20%."""
        mock_cursor = mocker.MagicMock()
        # total=100, null_price=10, null_location=5, null_title=8 -> max=10%
        mock_cursor.fetchone.return_value = (100, 10, 5, 8)
        mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = mocker.MagicMock(return_value=None)
        mocker.patch("korean_rental_etl.validation.thresholds.get_cursor", return_value=mock_cursor)

        result = check_null_rate_threshold(1, max_null_rate=0.20)
        assert result.passed is True

    def test_null_rate_fail(self, mocker):
        """Should fail when null_rate > 20%."""
        mock_cursor = mocker.MagicMock()
        # total=100, null_price=25, null_location=5, null_title=8 -> max=25%
        mock_cursor.fetchone.return_value = (100, 25, 5, 8)
        mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = mocker.MagicMock(return_value=None)
        mocker.patch("korean_rental_etl.validation.thresholds.get_cursor", return_value=mock_cursor)

        result = check_null_rate_threshold(1, max_null_rate=0.20)
        assert result.passed is False

    def test_fk_integrity_pass(self, mocker):
        """Should pass when no orphaned rows."""
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone.return_value = (0,)
        mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = mocker.MagicMock(return_value=None)
        mocker.patch("korean_rental_etl.validation.thresholds.get_cursor", return_value=mock_cursor)

        result = check_fk_integrity()
        assert result.passed is True

    def test_fk_integrity_fail(self, mocker):
        """Should fail when orphaned rows exist."""
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone.return_value = (5,)
        mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = mocker.MagicMock(return_value=None)
        mocker.patch("korean_rental_etl.validation.thresholds.get_cursor", return_value=mock_cursor)

        result = check_fk_integrity()
        assert result.passed is False

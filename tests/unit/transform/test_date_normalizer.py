"""Additional tests for transform/normalizers/date.py covering branches not exercised
by test_normalizers.py (relative-time variants, ISO/short/MM-DD-YYYY paths, ValueError
fallbacks, and the unparseable input default).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from korean_rental_etl.transform.normalizers.date import normalize_date


class TestRelativeDates:
    """Cover all relative-date branches."""

    def test_today_english(self) -> None:
        result = normalize_date("today")
        assert result["posted_at_utc"] is not None

    def test_yesterday_english(self) -> None:
        result = normalize_date("yesterday")
        before = datetime.now(UTC) - timedelta(days=1, hours=1)
        assert result["posted_at_utc"] is not None
        assert result["posted_at_utc"] >= before

    def test_just_now_korean(self) -> None:
        """방금 → today (covers the 방금 branch on line 36-37)."""
        result = normalize_date("방금 전")
        assert result["posted_at_utc"] is not None
        assert result["posted_at_utc"].date() == datetime.now(UTC).date()

    def test_just_now_english(self) -> None:
        """just now → today (case-insensitive)."""
        result = normalize_date("Just Now")
        assert result["posted_at_utc"] is not None
        assert result["posted_at_utc"].date() == datetime.now(UTC).date()


class TestKoreanFormat:
    """Cover Korean YYYY년 MM월 DD일 format including ValueError branch."""

    def test_korean_format_with_spaces(self) -> None:
        result = normalize_date("2024년 12월 31일")
        assert result["posted_at_utc"] == datetime(2024, 12, 31, tzinfo=UTC)

    def test_korean_format_invalid_day_returns_none(self) -> None:
        """Invalid day (Feb 30) hits the ValueError branch on lines 45-47."""
        result = normalize_date("2024년 2월 30일")
        assert result["posted_at_utc"] is None

    def test_korean_format_invalid_month_returns_none(self) -> None:
        """Invalid month (13) hits the ValueError branch."""
        result = normalize_date("2024년 13월 1일")
        assert result["posted_at_utc"] is None


class TestIsoFormat:
    """Cover ISO YYYY-MM-DD format including ValueError branch (lines 50-56)."""

    def test_iso_full_year(self) -> None:
        result = normalize_date("2026-05-19")
        assert result["posted_at_utc"] == datetime(2026, 5, 19, tzinfo=UTC)

    def test_iso_invalid_month_returns_none(self) -> None:
        """ISO with invalid month hits ValueError branch (lines 55-56)."""
        result = normalize_date("2024-13-01")
        assert result["posted_at_utc"] is None

    def test_iso_invalid_day_returns_none(self) -> None:
        """ISO with invalid day hits ValueError branch."""
        result = normalize_date("2024-02-30")
        assert result["posted_at_utc"] is None


class TestShortMmDdFormat:
    """Cover short MM-DD format (lines 58-65)."""

    def test_short_mm_dd_valid(self) -> None:
        """Short MM-DD assumes current year."""
        result = normalize_date("05-19")
        assert result["posted_at_utc"] is not None
        current_year = datetime.now(UTC).year
        assert result["posted_at_utc"] == datetime(current_year, 5, 19, tzinfo=UTC)

    def test_short_mm_dd_invalid_returns_none(self) -> None:
        """Short MM-DD with invalid month hits ValueError branch (lines 64-65)."""
        # 13-01 matches the regex (\d{2})-(\d{2}) but datetime() raises ValueError
        result = normalize_date("13-01")
        assert result["posted_at_utc"] is None

    def test_short_mm_dd_invalid_day_returns_none(self) -> None:
        result = normalize_date("02-30")
        assert result["posted_at_utc"] is None


class TestMmDdYyyyFormat:
    """Cover MM/DD/YYYY format (lines 67-74)."""

    def test_mm_dd_yyyy_valid(self) -> None:
        result = normalize_date("5/19/2026")
        assert result["posted_at_utc"] == datetime(2026, 5, 19, tzinfo=UTC)

    def test_mm_dd_yyyy_two_digit_month(self) -> None:
        result = normalize_date("12/31/2024")
        assert result["posted_at_utc"] == datetime(2024, 12, 31, tzinfo=UTC)

    def test_mm_dd_yyyy_invalid_month_returns_none(self) -> None:
        """MM/DD/YYYY with invalid month hits ValueError branch (lines 73-74)."""
        result = normalize_date("13/01/2024")
        assert result["posted_at_utc"] is None

    def test_mm_dd_yyyy_invalid_day_returns_none(self) -> None:
        result = normalize_date("2/30/2024")
        assert result["posted_at_utc"] is None


class TestUnparseable:
    """Cover the final fallback that returns None (line 76)."""

    def test_unparseable_text_returns_none(self) -> None:
        result = normalize_date("not a date at all")
        assert result["posted_at_utc"] is None

    def test_only_letters_returns_none(self) -> None:
        result = normalize_date("foobar")
        assert result["posted_at_utc"] is None

    def test_partial_korean_no_match_returns_none(self) -> None:
        # Has 년 but no full match
        result = normalize_date("2024년만")
        assert result["posted_at_utc"] is None

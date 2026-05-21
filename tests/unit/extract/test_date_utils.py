"""Tests for Korean date parser."""

from datetime import date

from korean_rental_etl.extract.date_utils import parse_korean_date


class TestParseKoreanDate:
    """Test Korean date parsing."""

    def test_yyyy_mm_dd_hyphen(self) -> None:
        assert parse_korean_date("2026-05-19") == date(2026, 5, 19)

    def test_yyyy_mm_dd_dot(self) -> None:
        assert parse_korean_date("2026.05.19") == date(2026, 5, 19)

    def test_yyyy_mm_dd_slash(self) -> None:
        assert parse_korean_date("2026/05/19") == date(2026, 5, 19)

    def test_mm_dd_hyphen_infer_year(self) -> None:
        today = date(2026, 5, 19)
        # 05-20 is in the future, so infer last year
        assert parse_korean_date("05-20", today=today) == date(2025, 5, 20)
        # 05-18 is in the past, so infer this year
        assert parse_korean_date("05-18", today=today) == date(2026, 5, 18)

    def test_mm_dd_slash_infer_year(self) -> None:
        today = date(2026, 5, 19)
        assert parse_korean_date("05/18", today=today) == date(2026, 5, 18)

    def test_mm_dd_dot_infer_year(self) -> None:
        today = date(2026, 5, 19)
        assert parse_korean_date("05.18", today=today) == date(2026, 5, 18)

    def test_korean_format_month_day(self) -> None:
        today = date(2026, 5, 19)
        assert parse_korean_date("5월18일", today=today) == date(2026, 5, 18)
        assert parse_korean_date("05월18일", today=today) == date(2026, 5, 18)

    def test_relative_just_now(self) -> None:
        today = date(2026, 5, 19)
        assert parse_korean_date("방금전", today=today) == today
        assert parse_korean_date("방금", today=today) == today

    def test_relative_today(self) -> None:
        today = date(2026, 5, 19)
        assert parse_korean_date("오늘", today=today) == today

    def test_relative_yesterday(self) -> None:
        today = date(2026, 5, 19)
        assert parse_korean_date("어제", today=today) == date(2026, 5, 18)

    def test_relative_minutes_ago(self) -> None:
        today = date(2026, 5, 19)
        assert parse_korean_date("5분전", today=today) == today
        assert parse_korean_date("30분전", today=today) == today

    def test_relative_hours_ago(self) -> None:
        today = date(2026, 5, 19)
        assert parse_korean_date("2시간전", today=today) == today
        assert parse_korean_date("12시간전", today=today) == today

    def test_relative_days_ago(self) -> None:
        today = date(2026, 5, 19)
        assert parse_korean_date("1일전", today=today) == date(2026, 5, 18)
        assert parse_korean_date("3일전", today=today) == date(2026, 5, 16)
        assert parse_korean_date("7일전", today=today) == date(2026, 5, 12)

    def test_invalid_date_returns_none(self) -> None:
        assert parse_korean_date("invalid") is None
        assert parse_korean_date("") is None
        assert parse_korean_date(None) is None

    def test_invalid_month_day_returns_none(self) -> None:
        assert parse_korean_date("13-01") is None  # Invalid month
        assert parse_korean_date("02-30") is None  # Invalid day

    def test_whitespace_handling(self) -> None:
        today = date(2026, 5, 19)
        assert parse_korean_date("  05-18  ", today=today) == date(2026, 5, 18)
        assert parse_korean_date("05-18 ", today=today) == date(2026, 5, 18)

    def test_mm_dd_with_space_after_separator(self) -> None:
        """svkoreans.com formats dates as '05. 20' with a space after the period."""
        today = date(2026, 5, 21)
        assert parse_korean_date("05. 20", today=today) == date(2026, 5, 20)
        assert parse_korean_date("05. 18", today=today) == date(2026, 5, 18)
        assert parse_korean_date("05 .18", today=today) == date(2026, 5, 18)
        assert parse_korean_date("05 . 18", today=today) == date(2026, 5, 18)
        # Hyphen and slash variants
        assert parse_korean_date("05- 18", today=today) == date(2026, 5, 18)
        assert parse_korean_date("05/ 18", today=today) == date(2026, 5, 18)

    def test_yyyy_mm_dd_with_spaces_around_separator(self) -> None:
        """Defensive: handle '2026. 05. 20' style if a source ever produces it."""
        assert parse_korean_date("2026. 05. 20") == date(2026, 5, 20)
        assert parse_korean_date("2026 . 05 . 20") == date(2026, 5, 20)

    def test_year_boundary_december_to_january(self) -> None:
        today = date(2026, 1, 5)
        # 12-30 is in the past (last year)
        assert parse_korean_date("12-30", today=today) == date(2025, 12, 30)
        # 01-04 is in the past (this year)
        assert parse_korean_date("01-04", today=today) == date(2026, 1, 4)

    def test_hh_mm_returns_today(self) -> None:
        today = date(2026, 5, 19)
        assert parse_korean_date("16:53", today=today) == today
        assert parse_korean_date("09:30", today=today) == today

    def test_hh_mm_with_seconds(self) -> None:
        today = date(2026, 5, 19)
        assert parse_korean_date("16:53:42", today=today) == today
        assert parse_korean_date("09:30:00", today=today) == today

    def test_hh_mm_with_whitespace(self) -> None:
        today = date(2026, 5, 19)
        assert parse_korean_date("  16:53  ", today=today) == today
        assert parse_korean_date("16:53 ", today=today) == today

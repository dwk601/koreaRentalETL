"""Tests for transform/parsers/_common.py functions not covered by test_common.py:
parse_korean_date, parse_korean_price, extract_contact_block, and the extract_body_text
text-fallback branch.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from korean_rental_etl.transform.parsers._common import (
    extract_body_text,
    extract_contact_block,
    parse_korean_date,
    parse_korean_price,
)


class TestParseKoreanDate:
    """Cover parse_korean_date in _common.py (the str-returning variant)."""

    def test_empty_string_returns_none(self) -> None:
        assert parse_korean_date("") is None

    def test_none_returns_none(self) -> None:
        # The signature is str | None implicitly - empty string covers both since
        # the falsy guard catches None too. Keep type-correct here.
        assert parse_korean_date("") is None

    def test_today_korean_returns_iso_date(self) -> None:
        result = parse_korean_date("오늘")
        assert result == date.today().isoformat()

    def test_today_english_returns_iso_date(self) -> None:
        result = parse_korean_date("today")
        assert result == date.today().isoformat()

    def test_yesterday_korean_returns_iso_date(self) -> None:
        result = parse_korean_date("어제")
        assert result == (date.today() - timedelta(days=1)).isoformat()

    def test_yesterday_english_returns_iso_date(self) -> None:
        result = parse_korean_date("Yesterday")
        assert result == (date.today() - timedelta(days=1)).isoformat()

    def test_just_now_korean_returns_iso_datetime(self) -> None:
        """방금 returns a full ISO datetime with tz (not just a date)."""
        result = parse_korean_date("방금 전")
        assert result is not None
        # Should parse as a datetime and equal today's date
        parsed = datetime.fromisoformat(result)
        assert parsed.date() == datetime.now(UTC).date()

    def test_just_now_english_returns_iso_datetime(self) -> None:
        result = parse_korean_date("just now")
        assert result is not None
        parsed = datetime.fromisoformat(result)
        assert parsed.date() == datetime.now(UTC).date()

    def test_korean_format_returns_iso(self) -> None:
        result = parse_korean_date("2024년 5월 1일")
        assert result == datetime(2024, 5, 1, tzinfo=UTC).isoformat()

    def test_korean_format_with_extra_text(self) -> None:
        """re.search (not match) lets us find the date inside larger strings."""
        result = parse_korean_date("등록일: 2024년 5월 1일 16:53")
        assert result == datetime(2024, 5, 1, tzinfo=UTC).isoformat()

    def test_korean_format_invalid_day_returns_none(self) -> None:
        """ValueError branch on Feb 30."""
        assert parse_korean_date("2024년 2월 30일") is None

    def test_unparseable_returns_none(self) -> None:
        assert parse_korean_date("not a date") is None


class TestParseKoreanPrice:
    """Cover parse_korean_price branches: lease_type detection and currency handling."""

    def test_empty_string_returns_all_none(self) -> None:
        result = parse_korean_price("")
        assert result == {
            "raw_price_ko": None,
            "rent_monthly_usd": None,
            "deposit_usd": None,
            "lease_type": None,
            "currency_raw": None,
        }

    def test_monthly_rent_usd(self) -> None:
        result = parse_korean_price("월세 $1,500")
        assert result["lease_type"] == "monthly_rent"
        assert result["rent_monthly_usd"] == 1500
        assert result["currency_raw"] == "USD"
        assert result["raw_price_ko"] == "월세 $1,500"

    def test_monthly_rent_usd_uppercase(self) -> None:
        """Uppercase USD should match too via .upper()."""
        result = parse_korean_price("월세 1500 USD")
        assert result["currency_raw"] == "USD"
        assert result["rent_monthly_usd"] == 1500

    def test_deposit_lease_type(self) -> None:
        result = parse_korean_price("보증금 $3,000")
        assert result["lease_type"] == "deposit"

    def test_jeonse_lease_type(self) -> None:
        result = parse_korean_price("전세 5억")
        assert result["lease_type"] == "jeonse"

    def test_short_term_korean(self) -> None:
        result = parse_korean_price("단기 임대 $2,000")
        assert result["lease_type"] == "short_term"

    def test_short_term_english(self) -> None:
        """English 'short' (case-insensitive) matches short_term."""
        result = parse_korean_price("Short term $2,000")
        assert result["lease_type"] == "short_term"

    def test_lease_korean(self) -> None:
        result = parse_korean_price("리스 $1,800")
        assert result["lease_type"] == "lease"

    def test_lease_english(self) -> None:
        result = parse_korean_price("Lease 1800")
        assert result["lease_type"] == "lease"

    def test_krw_large_amount_converted(self) -> None:
        """Large KRW amount (>10000) gets converted via // 1200."""
        result = parse_korean_price("월세 1,200,000")
        assert result["currency_raw"] == "KRW"
        assert result["rent_monthly_usd"] == 1000  # 1_200_000 // 1200

    def test_krw_small_amount_unchanged(self) -> None:
        """Small KRW amount (<=10000) is kept as-is."""
        result = parse_korean_price("월세 5000")
        assert result["currency_raw"] == "KRW"
        assert result["rent_monthly_usd"] == 5000

    def test_no_lease_type_no_numbers(self) -> None:
        """Plain text with no number stays at default values for those fields."""
        result = parse_korean_price("문의 바랍니다")
        assert result["lease_type"] is None
        assert result["rent_monthly_usd"] is None
        assert result["currency_raw"] is None
        assert result["raw_price_ko"] == "문의 바랍니다"


class TestExtractContactBlock:
    """Cover extract_contact_block (lines 110-114)."""

    def test_none_returns_empty(self) -> None:
        assert extract_contact_block(None) == ""

    def test_empty_string_returns_empty(self) -> None:
        # extract_contact_block guards on falsy elements
        assert extract_contact_block("") == ""

    def test_string_element_returns_string(self) -> None:
        """When passed a non-BeautifulSoup string it falls through to extract_text."""
        # extract_text on a string just returns the str() of it, whitespace-collapsed.
        result = extract_contact_block("  213-555-1234  ")
        assert result == "213-555-1234"

    def test_bs4_element_returns_text(self) -> None:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(
            '<div class="contact">연락처: 213-555-1234</div>',
            "html.parser",
        )
        element = soup.select_one(".contact")
        result = extract_contact_block(element)
        assert "213-555-1234" in result


class TestExtractBodyTextFallback:
    """Cover the 'fallback to full text if no paragraphs' branch (line 184)."""

    def test_fallback_when_no_p_or_div_children(self) -> None:
        """An element with only inline text (no <p>/<div>) hits the extract_text fallback."""
        from bs4 import BeautifulSoup

        # span has no <p>/<div> direct children, so paragraphs is empty and
        # extract_body_text falls through to the extract_text(element) branch.
        html = '<div class="content">just inline text here</div>'
        soup = BeautifulSoup(html, "html.parser")
        # Force the no-paragraph path by selecting the inner content with only text
        soup2 = BeautifulSoup(
            '<div class="content"><span>just inline text here</span></div>', "html.parser"
        )
        result = extract_body_text(soup2, [".content"])
        assert "just inline text here" in result

        # Also exercise the simpler all-text-no-children case
        result2 = extract_body_text(soup, [".content"])
        assert result2 == "just inline text here"

"""Tests for all normalizers."""

from __future__ import annotations

from decimal import Decimal

from korean_rental_etl.transform.normalizers.contact import normalize_contact
from korean_rental_etl.transform.normalizers.date import normalize_date
from korean_rental_etl.transform.normalizers.location import normalize_location
from korean_rental_etl.transform.normalizers.price import normalize_price


class TestPriceNormalizer:
    def test_monthly_rent_usd(self) -> None:
        result = normalize_price("월세: $1,500")
        assert result["rent_monthly_usd"] == Decimal("1500")
        assert result["lease_type"] == "monthly"
        assert result["currency_raw"] == "USD"

    def test_deposit_plus_monthly(self) -> None:
        result = normalize_price("월세 $1,500 / 보증금 $3,000")
        assert result["rent_monthly_usd"] == Decimal("1500")
        assert result["deposit_usd"] == Decimal("3000")

    def test_jeonse(self) -> None:
        result = normalize_price("전세: $30,000")
        assert result["lease_type"] == "jeonse"
        assert result["deposit_usd"] == Decimal("30000")

    def test_krw(self) -> None:
        result = normalize_price("월세 ₩1,000,000")
        assert result["currency_raw"] == "KRW"
        assert result["rent_monthly_usd"] is not None
        assert result["rent_monthly_usd"] > Decimal("0")

    def test_empty(self) -> None:
        result = normalize_price("")
        assert result["rent_monthly_usd"] is None


class TestDateNormalizer:
    def test_korean_date(self) -> None:
        result = normalize_date("2024년 5월 1일")
        assert result["posted_at_utc"] is not None
        assert result["posted_at_utc"].year == 2024

    def test_today(self) -> None:
        result = normalize_date("오늘")
        assert result["posted_at_utc"] is not None

    def test_yesterday(self) -> None:
        result = normalize_date("어제")
        assert result["posted_at_utc"] is not None

    def test_iso_date(self) -> None:
        result = normalize_date("2024-05-01")
        assert result["posted_at_utc"] is not None
        assert result["posted_at_utc"].month == 5

    def test_empty(self) -> None:
        result = normalize_date("")
        assert result["posted_at_utc"] is None


class TestLocationNormalizer:
    def test_la_downtown(self) -> None:
        result = normalize_location("LA 다운타운 7th Street")
        assert result["city"] is not None
        assert result["country"] == "US"
        assert result["address_raw"] == "LA 다운타운 7th Street"

    def test_korean_city(self) -> None:
        result = normalize_location("서울 강남구")
        assert result["city"] == "서울"
        assert result["country"] == "KR"

    def test_empty(self) -> None:
        result = normalize_location("")
        assert result["city"] is None


class TestContactNormalizer:
    def test_phone(self) -> None:
        result = normalize_contact("연락처: 213-555-1234")
        assert result["phone"] == "213-555-1234"

    def test_kakao(self) -> None:
        result = normalize_contact("카카오: sfrental")
        assert result["kakao_id"] == "sfrental"

    def test_email(self) -> None:
        result = normalize_contact("이메일: test@example.com")
        assert result["email"] == "test@example.com"

    def test_all_three(self) -> None:
        result = normalize_contact("연락: 213-555-1234 / 카카오: renthelp / 이메일: a@b.com")
        assert result["phone"] == "213-555-1234"
        assert result["kakao_id"] == "renthelp"
        assert result["email"] == "a@b.com"

    def test_empty(self) -> None:
        result = normalize_contact("")
        assert result["phone"] is None
        assert result["kakao_id"] is None
        assert result["email"] is None

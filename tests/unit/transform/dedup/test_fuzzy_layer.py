"""Unit tests for fuzzy dedup layer."""

from datetime import datetime, timedelta, timezone

import pytest

from korean_rental_etl.transform.dedup.fuzzy_layer import find_duplicates


class TestFuzzyLayer:
    """Test fuzzy dedup with time-window blocking."""

    def test_clear_duplicates_same_city_same_day(self):
        """Should mark identical listings in same city/day as duplicates."""
        now = datetime.now(timezone.utc).isoformat()
        listings = [
            {
                "id": 1,
                "title_ko": "강남 아파트 2룸",
                "rent_monthly_usd": 1500,
                "city": "Seoul",
                "posted_at_utc": now,
            },
            {
                "id": 2,
                "title_ko": "강남 아파트 2룸",
                "rent_monthly_usd": 1500,
                "city": "Seoul",
                "posted_at_utc": now,
            },
        ]

        result = find_duplicates(listings)
        assert len(result) == 2
        assert result[0]["is_duplicate"] is False
        assert result[1]["is_duplicate"] is True
        assert result[1]["canonical_id"] == 1

    def test_time_window_edge_6_days(self):
        """Should match listings 6 days apart (within window)."""
        now = datetime.now(timezone.utc)
        date_a = now.isoformat()
        date_b = (now - timedelta(days=6)).isoformat()

        listings = [
            {
                "id": 1,
                "title_ko": "아파트 2룸",
                "rent_monthly_usd": 1500,
                "city": "Seoul",
                "posted_at_utc": date_a,
            },
            {
                "id": 2,
                "title_ko": "아파트 2룸",
                "rent_monthly_usd": 1500,
                "city": "Seoul",
                "posted_at_utc": date_b,
            },
        ]

        result = find_duplicates(listings)
        duplicates = [r for r in result if r["is_duplicate"]]
        assert len(duplicates) == 1

    def test_time_window_edge_8_days(self):
        """Should NOT match listings 8 days apart (outside window)."""
        now = datetime.now(timezone.utc)
        date_a = now.isoformat()
        date_b = (now - timedelta(days=8)).isoformat()

        listings = [
            {
                "id": 1,
                "title_ko": "아파트 2룸",
                "rent_monthly_usd": 1500,
                "city": "Seoul",
                "posted_at_utc": date_a,
            },
            {
                "id": 2,
                "title_ko": "아파트 2룸",
                "rent_monthly_usd": 1500,
                "city": "Seoul",
                "posted_at_utc": date_b,
            },
        ]

        result = find_duplicates(listings)
        duplicates = [r for r in result if r["is_duplicate"]]
        assert len(duplicates) == 0

    def test_near_miss_below_threshold(self):
        """Should NOT match listings below similarity threshold."""
        now = datetime.now(timezone.utc).isoformat()
        listings = [
            {
                "id": 1,
                "title_ko": "강남 아파트 2룸",
                "rent_monthly_usd": 1500,
                "city": "Seoul",
                "posted_at_utc": now,
            },
            {
                "id": 2,
                "title_ko": "강남 오피스텔 1룸",
                "rent_monthly_usd": 1200,
                "city": "Seoul",
                "posted_at_utc": now,
            },
        ]

        result = find_duplicates(listings)
        duplicates = [r for r in result if r["is_duplicate"]]
        assert len(duplicates) == 0

    def test_different_cities_no_match(self):
        """Should NOT match listings in different cities."""
        now = datetime.now(timezone.utc).isoformat()
        listings = [
            {
                "id": 1,
                "title_ko": "아파트 2룸",
                "rent_monthly_usd": 1500,
                "city": "Seoul",
                "posted_at_utc": now,
            },
            {
                "id": 2,
                "title_ko": "아파트 2룸",
                "rent_monthly_usd": 1500,
                "city": "Busan",
                "posted_at_utc": now,
            },
        ]

        result = find_duplicates(listings)
        duplicates = [r for r in result if r["is_duplicate"]]
        assert len(duplicates) == 0

    def test_canonical_earliest_posted_at(self):
        """Should pick canonical as earliest posted_at."""
        now = datetime.now(timezone.utc)
        date_a = (now - timedelta(days=2)).isoformat()
        date_b = now.isoformat()

        listings = [
            {
                "id": 1,
                "title_ko": "아파트 2룸",
                "rent_monthly_usd": 1500,
                "city": "Seoul",
                "posted_at_utc": date_b,
            },
            {
                "id": 2,
                "title_ko": "아파트 2룸",
                "rent_monthly_usd": 1500,
                "city": "Seoul",
                "posted_at_utc": date_a,
            },
        ]

        result = find_duplicates(listings)
        canonical = [r for r in result if not r["is_duplicate"]][0]
        assert canonical["id"] == 2

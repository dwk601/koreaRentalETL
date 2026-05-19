"""Tests for BaseScraper cutoff logic."""

from datetime import date, timedelta

from korean_rental_etl.extract.base_scraper import BaseScraper


class MockScraper(BaseScraper):
    """Mock scraper for testing."""

    source_name = "test"

    def crawl_list_pages(self):
        return iter([])

    def fetch_detail(self, url: str):
        return {"html": "", "status": 200, "url": url}


class TestCutoffLogic:
    """Test 30-day cutoff filtering."""

    def test_within_cutoff_recent_date(self) -> None:
        scraper = MockScraper(source_id=1)
        today = date.today()
        recent = today - timedelta(days=5)
        assert scraper._within_cutoff(recent) is True

    def test_within_cutoff_boundary_date(self) -> None:
        scraper = MockScraper(source_id=1)
        today = date.today()
        boundary = today - timedelta(days=30)
        assert scraper._within_cutoff(boundary) is True

    def test_outside_cutoff_old_date(self) -> None:
        scraper = MockScraper(source_id=1)
        today = date.today()
        old = today - timedelta(days=31)
        assert scraper._within_cutoff(old) is False

    def test_within_cutoff_today(self) -> None:
        scraper = MockScraper(source_id=1)
        today = date.today()
        assert scraper._within_cutoff(today) is True

    def test_within_cutoff_none_date(self) -> None:
        scraper = MockScraper(source_id=1)
        assert scraper._within_cutoff(None) is True

    def test_within_cutoff_non_date_object(self) -> None:
        scraper = MockScraper(source_id=1)
        assert scraper._within_cutoff("not a date") is True
        assert scraper._within_cutoff(123) is True

    def test_custom_cutoff_days(self) -> None:
        scraper = MockScraper(source_id=1)
        scraper.cutoff_days = 7
        today = date.today()
        old = today - timedelta(days=8)
        assert scraper._within_cutoff(old) is False
        recent = today - timedelta(days=6)
        assert scraper._within_cutoff(recent) is True

"""Tests for BaseScraper cutoff logic."""

from datetime import date, timedelta
from unittest.mock import patch

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

    def test_env_var_overrides_default(self, monkeypatch) -> None:
        """Test that EXTRACT_CUTOFF_DAYS env var overrides default."""
        monkeypatch.setenv("EXTRACT_CUTOFF_DAYS", "7")
        scraper = MockScraper(source_id=1)
        assert scraper.cutoff_days == 7

    def test_extract_skips_stale_listings(self, monkeypatch) -> None:
        """Test that extract() skips listings outside cutoff window."""
        monkeypatch.setenv("EXTRACT_CUTOFF_DAYS", "30")

        today = date.today()
        fresh_date = today - timedelta(days=5)
        stale_date = today - timedelta(days=60)

        class TestScraper(MockScraper):
            def crawl_list_pages(self):
                return iter(
                    [
                        {
                            "url": "http://fresh.com",
                            "source_listing_id": "1",
                            "title": "Fresh",
                            "post_date": fresh_date,
                        },
                        {
                            "url": "http://stale.com",
                            "source_listing_id": "2",
                            "title": "Stale",
                            "post_date": stale_date,
                        },
                    ]
                )

        scraper = TestScraper(source_id=1)
        with (
            patch("korean_rental_etl.load.audit.start_run") as mock_start,
            patch("korean_rental_etl.load.audit.finish_run") as mock_finish,
            patch("korean_rental_etl.transform.dedup.redis_layer.seen") as mock_seen,
            patch("korean_rental_etl.transform.dedup.redis_layer.mark") as mock_mark,
            patch("korean_rental_etl.extract.raw_writer.save") as mock_save,
        ):
            mock_start.return_value = 1
            mock_seen.return_value = False
            mock_save.return_value = True
            del mock_finish, mock_mark  # Unused

            extracted, skipped = scraper.extract()

            # Only fresh URL should be saved
            assert mock_save.call_count == 1
            assert skipped == 1  # Stale URL skipped

    def test_extract_keeps_listings_with_none_post_date(self, monkeypatch) -> None:
        """Test that extract() keeps listings with post_date=None."""
        monkeypatch.setenv("EXTRACT_CUTOFF_DAYS", "30")

        class TestScraper(MockScraper):
            def crawl_list_pages(self):
                return iter(
                    [
                        {
                            "url": "http://unknown.com",
                            "source_listing_id": "1",
                            "title": "Unknown Date",
                            "post_date": None,
                        },
                    ]
                )

        scraper = TestScraper(source_id=1)
        with (
            patch("korean_rental_etl.load.audit.start_run") as mock_start,
            patch("korean_rental_etl.load.audit.finish_run") as mock_finish,
            patch("korean_rental_etl.transform.dedup.redis_layer.seen") as mock_seen,
            patch("korean_rental_etl.transform.dedup.redis_layer.mark") as mock_mark,
            patch("korean_rental_etl.extract.raw_writer.save") as mock_save,
        ):
            mock_start.return_value = 1
            mock_seen.return_value = False
            mock_save.return_value = True
            del mock_finish, mock_mark  # Unused

            extracted, skipped = scraper.extract()

            # URL with None post_date should be processed
            assert mock_save.call_count == 1
            assert extracted == 1

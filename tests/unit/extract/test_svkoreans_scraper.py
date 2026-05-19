"""Tests for svkoreans scraper using HTML fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from korean_rental_etl.extract.scrapers.svkoreans import SvkoreansScraper

FIXTURES_DIR = (
    Path(__file__).parent.parent.parent.parent / "tests" / "fixtures" / "html" / "svkoreans"
)


class TestSvkoreansScraper:
    @pytest.fixture
    def scraper(self) -> SvkoreansScraper:
        return SvkoreansScraper(source_id=1)

    def test_crawl_list_pages_from_fixture(self, scraper: SvkoreansScraper) -> None:
        listings = list(scraper.crawl_list_pages())
        assert len(listings) == 3

        # Check first listing
        assert listings[0]["url"].startswith("https://svkoreans.com/")
        assert "12345" in listings[0]["source_listing_id"]
        assert "LA" in listings[0]["title"]
        assert "다운타운" in listings[0]["title"]

    def test_listing_urls_are_absolute(self, scraper: SvkoreansScraper) -> None:
        listings = list(scraper.crawl_list_pages())
        for listing in listings:
            assert listing["url"].startswith("http")
            assert "view" in listing["url"]

    def test_listing_ids_unique(self, scraper: SvkoreansScraper) -> None:
        listings = list(scraper.crawl_list_pages())
        ids = [listing["source_listing_id"] for listing in listings]
        assert len(ids) == len(set(ids))


class TestDetailPages:
    def test_detail_page_12345(self) -> None:
        fixture = FIXTURES_DIR / "detail_12345.html"
        html = fixture.read_text()
        assert "다운타운" in html
        assert "$1,500" in html
        assert "213-555-1234" in html

    def test_detail_page_12346(self) -> None:
        fixture = FIXTURES_DIR / "detail_12346.html"
        html = fixture.read_text()
        assert "어바인" in html
        assert "$2,800" in html
        assert "949-555-5678" in html

    def test_detail_page_12347(self) -> None:
        fixture = FIXTURES_DIR / "detail_12347.html"
        html = fixture.read_text()
        assert "샌프란시스코" in html
        assert "$2,500" in html
        assert "sfrental" in html

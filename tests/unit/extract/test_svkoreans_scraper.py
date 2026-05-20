"""Tests for svkoreans scraper using HTML fixtures (offline)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from korean_rental_etl.extract.scrapers.svkoreans import SvkoreansScraper

FIXTURES_DIR = (
    Path(__file__).parent.parent.parent.parent / "tests" / "fixtures" / "html" / "svkoreans"
)


def _force_fixture(monkeypatch: pytest.MonkeyPatch, scraper: Any) -> None:
    def _raise(*_: Any, **__: Any) -> None:
        raise RuntimeError("network disabled in unit tests")

    monkeypatch.setattr(scraper, "fetch_page", _raise)


class TestSvkoreansScraper:
    @pytest.fixture
    def scraper(self, monkeypatch: pytest.MonkeyPatch) -> SvkoreansScraper:
        s = SvkoreansScraper(source_id=1)
        _force_fixture(monkeypatch, s)
        return s

    def test_crawl_list_pages_from_fixture(self, scraper: SvkoreansScraper) -> None:
        listings = list(scraper.crawl_list_pages())
        assert len(listings) >= 3, f"Expected at least 3 listings, got {len(listings)}"

        url_pattern = re.compile(r"^https://svkoreans\.com/rent_housing/\d+$")
        korean_pattern = re.compile(r"[\uac00-\ud7af]")
        for listing in listings:
            assert "url" in listing
            assert "source_listing_id" in listing
            assert "title" in listing
            assert url_pattern.match(listing["url"]), f"Bad URL: {listing['url']}"
            assert listing["source_listing_id"].isdigit()
            assert len(listing["title"]) > 0
            assert korean_pattern.search(listing["title"]), (
                f"Title should contain Korean characters: {listing['title']!r}"
            )

    def test_listing_urls_are_absolute(self, scraper: SvkoreansScraper) -> None:
        listings = list(scraper.crawl_list_pages())
        for listing in listings:
            assert listing["url"].startswith("https://svkoreans.com/rent_housing/")

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

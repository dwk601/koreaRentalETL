"""Tests for all remaining scrapers using HTML fixtures."""

from __future__ import annotations

import pytest

from korean_rental_etl.extract.scrapers.gtksa import GtksaScraper
from korean_rental_etl.extract.scrapers.ktown_koreadaily import KtownKoreadailyScraper
from korean_rental_etl.extract.scrapers.missyusa import MissyusaScraper
from korean_rental_etl.extract.scrapers.radiokorea import RadiokoreaScraper


class TestGtksaScraper:
    @pytest.fixture
    def scraper(self) -> GtksaScraper:
        return GtksaScraper(source_id=2)

    def test_crawl_list_pages(self, scraper: GtksaScraper) -> None:
        listings = list(scraper.crawl_list_pages())
        assert len(listings) == 3
        assert all(listing["url"].startswith("https://gtksa.net/") for listing in listings)


class TestMissyusaScraper:
    @pytest.fixture
    def scraper(self) -> MissyusaScraper:
        return MissyusaScraper(source_id=3)

    def test_crawl_list_pages(self, scraper: MissyusaScraper) -> None:
        listings = list(scraper.crawl_list_pages())
        assert len(listings) == 3
        assert all(listing["url"].startswith("https://missyusa.com/") for listing in listings)


class TestKtownKoreadailyScraper:
    @pytest.fixture
    def scraper(self) -> KtownKoreadailyScraper:
        return KtownKoreadailyScraper(source_id=4)

    def test_crawl_list_pages(self, scraper: KtownKoreadailyScraper) -> None:
        listings = list(scraper.crawl_list_pages())
        assert len(listings) == 3
        assert all(listing["url"].startswith("https://ktown.koreadaily.com/") for listing in listings)


class TestRadiokoreaScraper:
    @pytest.fixture
    def scraper(self) -> RadiokoreaScraper:
        return RadiokoreaScraper(source_id=5)

    def test_crawl_list_pages(self, scraper: RadiokoreaScraper) -> None:
        listings = list(scraper.crawl_list_pages())
        assert len(listings) == 3
        assert all(listing["url"].startswith("https://m.radiokorea.com/") for listing in listings)


class TestExtractAll:
    def test_all_scrapers_have_listings(self) -> None:
        scrapers = [
            GtksaScraper(source_id=2),
            MissyusaScraper(source_id=3),
            KtownKoreadailyScraper(source_id=4),
            RadiokoreaScraper(source_id=5),
        ]
        for scraper in scrapers:
            listings = list(scraper.crawl_list_pages())
            assert len(listings) >= 1, f"{scraper.source_name} has no listings"
            assert all("url" in listing for listing in listings)
            assert all("source_listing_id" in listing for listing in listings)

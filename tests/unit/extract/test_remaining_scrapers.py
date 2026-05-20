"""Tests for all remaining scrapers using HTML fixtures (offline)."""

from __future__ import annotations

from typing import Any

import pytest

from korean_rental_etl.extract.scrapers.gtksa import GtksaScraper
from korean_rental_etl.extract.scrapers.ktown_koreadaily import KtownKoreadailyScraper
from korean_rental_etl.extract.scrapers.missyusa import MissyusaScraper
from korean_rental_etl.extract.scrapers.radiokorea import RadiokoreaScraper


def _force_fixture(monkeypatch: pytest.MonkeyPatch, scraper: Any) -> None:
    """Make `fetch_page` raise so the scraper falls through to its fixture path.

    Unit tests must be hermetic - they should not hit the network.
    """

    def _raise(*_: Any, **__: Any) -> None:  # pragma: no cover - trivial
        raise RuntimeError("network disabled in unit tests")

    monkeypatch.setattr(scraper, "fetch_page", _raise)


class TestGtksaScraper:
    @pytest.fixture
    def scraper(self, monkeypatch: pytest.MonkeyPatch) -> GtksaScraper:
        s = GtksaScraper(source_id=2)
        _force_fixture(monkeypatch, s)
        return s

    def test_crawl_list_pages(self, scraper: GtksaScraper) -> None:
        listings = list(scraper.crawl_list_pages())
        assert len(listings) >= 3, f"Expected at least 3 listings, got {len(listings)}"

        for listing in listings:
            assert "url" in listing
            assert "source_listing_id" in listing
            assert "title" in listing
            assert listing["url"].startswith("https://gtksa.net/")
            assert "wr_id=" in listing["url"]
            assert listing["source_listing_id"].isdigit()
            assert len(listing["title"]) > 0


class TestMissyusaScraper:
    @pytest.fixture
    def scraper(self, monkeypatch: pytest.MonkeyPatch) -> MissyusaScraper:
        s = MissyusaScraper(source_id=3)
        _force_fixture(monkeypatch, s)
        return s

    def test_crawl_list_pages(self, scraper: MissyusaScraper) -> None:
        listings = list(scraper.crawl_list_pages())
        assert len(listings) >= 3, f"Expected at least 3 listings, got {len(listings)}"

        seen_ids: set[str] = set()
        for listing in listings:
            assert "url" in listing
            assert "source_listing_id" in listing
            assert "title" in listing
            assert listing["url"].startswith("https://www.missyusa.com/")
            assert "board_read.asp" in listing["url"]
            assert "idx=" in listing["url"]
            assert len(listing["title"]) > 0
            # IDs must be unique per page
            assert listing["source_listing_id"] not in seen_ids
            seen_ids.add(listing["source_listing_id"])


class TestKtownKoreadailyScraper:
    @pytest.fixture
    def scraper(self, monkeypatch: pytest.MonkeyPatch) -> KtownKoreadailyScraper:
        s = KtownKoreadailyScraper(source_id=4)
        _force_fixture(monkeypatch, s)
        return s

    def test_crawl_list_pages(self, scraper: KtownKoreadailyScraper) -> None:
        listings = list(scraper.crawl_list_pages())
        assert len(listings) >= 3, f"Expected at least 3 listings, got {len(listings)}"

        urls = []
        for listing in listings:
            assert "url" in listing
            assert "source_listing_id" in listing
            assert "title" in listing
            assert listing["url"].startswith("https://ktown.koreadaily.com/")
            assert "/ad_rent/rentview?data=" in listing["url"]
            assert listing["source_listing_id"].isdigit()
            assert len(listing["title"]) > 0
            urls.append(listing["url"])
        assert len(urls) == len(set(urls)), "URLs must be deduplicated"


class TestRadiokoreaScraper:
    @pytest.fixture
    def scraper(self, monkeypatch: pytest.MonkeyPatch) -> RadiokoreaScraper:
        s = RadiokoreaScraper(source_id=5)
        _force_fixture(monkeypatch, s)
        return s

    def test_crawl_list_pages(self, scraper: RadiokoreaScraper) -> None:
        listings = list(scraper.crawl_list_pages())
        assert len(listings) >= 3, f"Expected at least 3 listings, got {len(listings)}"

        for listing in listings:
            assert "url" in listing
            assert "source_listing_id" in listing
            assert "title" in listing
            assert listing["url"].startswith("https://radiokorea.com/")
            assert "wr_id=" in listing["url"]
            assert listing["source_listing_id"].isdigit()
            assert len(listing["title"]) > 0
            # Must not pick up notice rows
            assert "[공지]" not in listing["title"]


class TestExtractAll:
    def test_all_scrapers_have_listings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        scrapers = [
            GtksaScraper(source_id=2),
            MissyusaScraper(source_id=3),
            KtownKoreadailyScraper(source_id=4),
            RadiokoreaScraper(source_id=5),
        ]
        for scraper in scrapers:
            _force_fixture(monkeypatch, scraper)
            listings = list(scraper.crawl_list_pages())
            assert len(listings) >= 1, f"{scraper.source_name} has no listings"
            assert all("url" in listing for listing in listings)
            assert all("source_listing_id" in listing for listing in listings)


class TestLocationSignal:
    """Verify all scrapers emit a 'location' field via _build_listing."""

    def test_all_scrapers_emit_location_field(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from korean_rental_etl.extract.scrapers.svkoreans import SvkoreansScraper
        from korean_rental_etl.text_utils import extract_title_bracket

        scrapers = [
            SvkoreansScraper(source_id=1),
            GtksaScraper(source_id=2),
            MissyusaScraper(source_id=3),
            KtownKoreadailyScraper(source_id=4),
            RadiokoreaScraper(source_id=5),
        ]
        for scraper in scrapers:
            _force_fixture(monkeypatch, scraper)
            listings = list(scraper.crawl_list_pages())
            assert len(listings) >= 1, f"{scraper.source_name} has no listings"
            for listing in listings:
                assert "location" in listing, (
                    f"{scraper.source_name} listing missing 'location' key: {listing}"
                )
                # location must equal the bracket extracted from the title
                expected = extract_title_bracket(listing["title"])
                assert listing["location"] == expected, (
                    f"{scraper.source_name}: location {listing['location']!r} != "
                    f"bracket {expected!r} for title {listing['title']!r}"
                )

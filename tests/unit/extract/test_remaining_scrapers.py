"""Tests for all remaining scrapers using HTML fixtures (offline)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

import pytest

from korean_rental_etl.extract.scrapers.gtksa import GtksaScraper
from korean_rental_etl.extract.scrapers.illinoisksa import IllinoisksaScraper
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
            assert "page=" not in listing["url"]
            assert listing["source_listing_id"].isdigit()
            assert len(listing["title"]) > 0
            # Must not pick up notice rows
            assert "[공지]" not in listing["title"]
            # Ensure post_date parses successfully
            assert listing.get("post_date") is not None

    def test_canonicalize_detail_url_strips_page(self) -> None:
        from korean_rental_etl.extract.scrapers.radiokorea import _canonicalize_detail_url

        # Strips page param when it is the last param
        assert (
            _canonicalize_detail_url(
                "https://radiokorea.com/bulletin/bbs/board.php?bo_table=c_realestate&wr_id=2642968&page=8"
            )
            == "https://radiokorea.com/bulletin/bbs/board.php?bo_table=c_realestate&wr_id=2642968"
        )

        # Idempotent on URLs without page=
        assert (
            _canonicalize_detail_url(
                "https://radiokorea.com/bulletin/bbs/board.php?bo_table=c_realestate&wr_id=2642968"
            )
            == "https://radiokorea.com/bulletin/bbs/board.php?bo_table=c_realestate&wr_id=2642968"
        )

        # Preserves other params (e.g. sca=foo)
        assert (
            _canonicalize_detail_url(
                "https://radiokorea.com/bulletin/bbs/board.php?bo_table=c_realestate&wr_id=2642968&sca=foo&page=8"
            )
            == "https://radiokorea.com/bulletin/bbs/board.php?bo_table=c_realestate&wr_id=2642968&sca=foo"
        )

        # Strips page even when it is the first param
        assert (
            _canonicalize_detail_url(
                "https://radiokorea.com/bulletin/bbs/board.php?page=8&bo_table=c_realestate&wr_id=2642968"
            )
            == "https://radiokorea.com/bulletin/bbs/board.php?bo_table=c_realestate&wr_id=2642968"
        )

        # Strips when it is the only param
        assert (
            _canonicalize_detail_url("https://radiokorea.com/bulletin/bbs/board.php?page=8")
            == "https://radiokorea.com/bulletin/bbs/board.php"
        )

    def test_max_pages_is_3(self, scraper: RadiokoreaScraper) -> None:
        assert scraper.max_pages == 3

    def test_pagination_stops_on_stale_row(
        self, scraper: RadiokoreaScraper, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Force all dates to be stale
        monkeypatch.setattr(scraper, "_within_cutoff", lambda *args, **kwargs: False)

        # Track paginated URLs visited
        visited_urls = []
        original_paginated_list_urls = scraper._paginated_list_urls

        def mock_paginated_list_urls() -> Iterator[str]:
            for url in original_paginated_list_urls():
                visited_urls.append(url)
                yield url

        monkeypatch.setattr(scraper, "_paginated_list_urls", mock_paginated_list_urls)

        # Run crawler
        listings = list(scraper.crawl_list_pages())

        # Confirm we have listing rows from page 1 but stopped pagination after encountering stale rows
        assert len(listings) >= 3
        # Confirm we only visited the first page
        assert len(visited_urls) == 1


class TestExtractAll:
    def test_all_scrapers_have_listings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        scrapers = [
            GtksaScraper(source_id=2),
            MissyusaScraper(source_id=3),
            KtownKoreadailyScraper(source_id=4),
            RadiokoreaScraper(source_id=5),
            IllinoisksaScraper(source_id=6),
        ]
        for scraper in scrapers:
            _force_fixture(monkeypatch, scraper)
            listings = list(scraper.crawl_list_pages())
            assert len(listings) >= 1, f"{scraper.source_name} has no listings"
            assert all("url" in listing for listing in listings)
            assert all("source_listing_id" in listing for listing in listings)


class TestLocationSignal:
    """Verify all scrapers emit a 'location' field via _build_listing."""

    def test_all_scrapers_emit_location_field(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from korean_rental_etl.extract.scrapers.svkoreans import SvkoreansScraper
        from korean_rental_etl.text_utils import extract_title_bracket

        scrapers = [
            SvkoreansScraper(source_id=1),
            GtksaScraper(source_id=2),
            MissyusaScraper(source_id=3),
            KtownKoreadailyScraper(source_id=4),
            RadiokoreaScraper(source_id=5),
            IllinoisksaScraper(source_id=6),
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

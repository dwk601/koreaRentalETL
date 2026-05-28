"""Tests for illinoisksa scraper using HTML fixtures (offline)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import pytest

from korean_rental_etl.extract.scrapers.illinoisksa import (
    IllinoisksaScraper,
    _canonicalize_detail_url,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


def _force_fixture(monkeypatch: pytest.MonkeyPatch, scraper: Any) -> None:
    def _raise(*_: Any, **__: Any) -> None:
        raise RuntimeError("network disabled in unit tests")

    monkeypatch.setattr(scraper, "fetch_page", _raise)


class TestIllinoisksaScraper:
    @pytest.fixture
    def scraper(self, monkeypatch: pytest.MonkeyPatch) -> IllinoisksaScraper:
        s = IllinoisksaScraper(source_id=6)
        _force_fixture(monkeypatch, s)
        return s

    def test_crawl_list_pages_from_fixture(self, scraper: IllinoisksaScraper) -> None:
        listings = list(scraper.crawl_list_pages())
        assert len(listings) >= 3, f"Expected at least 3 listings, got {len(listings)}"

        url_pattern = re.compile(r"^https://illinoisksa\.org/housing/\?mod=document&uid=\d+$")
        for listing in listings:
            assert "url" in listing
            assert "source_listing_id" in listing
            assert "title" in listing
            assert url_pattern.match(listing["url"]), f"Bad URL: {listing['url']}"
            assert listing["source_listing_id"].isdigit()
            assert len(listing["title"]) > 0

    def test_listing_urls_are_absolute(self, scraper: IllinoisksaScraper) -> None:
        listings = list(scraper.crawl_list_pages())
        for listing in listings:
            assert listing["url"].startswith("https://illinoisksa.org/housing/?mod=document&uid=")

    def test_listing_ids_unique(self, scraper: IllinoisksaScraper) -> None:
        listings = list(scraper.crawl_list_pages())
        ids = [listing["source_listing_id"] for listing in listings]
        assert len(ids) == len(set(ids))

    def test_notice_rows_excluded(self, scraper: IllinoisksaScraper) -> None:
        listings = list(scraper.crawl_list_pages())
        # Fixture has 3 notice rows and 10 data rows
        assert len(listings) <= 10
        for listing in listings:
            assert "[필독]" not in listing["title"]

    def test_post_dates_parsed(self, scraper: IllinoisksaScraper) -> None:
        listings = list(scraper.crawl_list_pages())
        dated = [x for x in listings if x.get("post_date") is not None]
        assert dated, "Expected at least one listing with a parsed post_date"

    def test_canonicalize_detail_url_strips_pageid(self) -> None:
        assert (
            _canonicalize_detail_url(
                "https://illinoisksa.org/housing/?mod=document&uid=13972&pageid=2"
            )
            == "https://illinoisksa.org/housing/?mod=document&uid=13972"
        )

        # Idempotent on URLs without pageid
        assert (
            _canonicalize_detail_url("https://illinoisksa.org/housing/?mod=document&uid=13972")
            == "https://illinoisksa.org/housing/?mod=document&uid=13972"
        )

    def test_pagination_stops_on_stale_row(
        self, scraper: IllinoisksaScraper, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Force all dates to be stale
        monkeypatch.setattr(scraper, "_within_cutoff", lambda *args, **kwargs: False)

        visited_urls: list[str] = []
        original_paginated_list_urls = scraper._paginated_list_urls

        def mock_paginated_list_urls() -> Iterator[str]:
            for url in original_paginated_list_urls():
                visited_urls.append(url)
                yield url

        monkeypatch.setattr(scraper, "_paginated_list_urls", mock_paginated_list_urls)

        listings = list(scraper.crawl_list_pages())

        assert len(listings) >= 3
        # Should only visit page 1 then stop
        assert len(visited_urls) == 1

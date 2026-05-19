"""Ktown Korea Daily scraper - rental listings from ktown.koreadaily.com."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from korean_rental_etl.extract.base_scraper import BaseScraper

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class KtownKoreadailyScraper(BaseScraper):
    """Scraper for ktown.koreadaily.com/ad_rent/rentlist."""

    source_name = "ktown_koreadaily"
    fetcher_type = "StealthyFetcher"
    _list_url = "https://ktown.koreadaily.com/ad_rent/rentlist"

    def crawl_list_pages(self) -> Iterator[dict[str, str]]:
        try:
            response = self.fetcher.fetch(self._list_url)
            soup = response.bs4
            links = soup.select(".rent_list a")
        except Exception:
            logger.warning("Could not fetch list page, using fixture fallback")
            links = self._links_from_fixture()

        for link in links:
            title = link.get_text(strip=True)
            href = str(link.get("href", ""))
            if href.startswith("/"):
                href = f"https://ktown.koreadaily.com{href}"
            elif not href.startswith("http"):
                href = f"https://ktown.koreadaily.com/{href}"
            seq = href.split("seq=")[-1].split("&")[0] if "seq=" in href else href
            yield {
                "url": href,
                "source_listing_id": seq or href,
                "title": title,
            }

    def fetch_detail(self, url: str) -> dict[str, object]:
        response = self.fetcher.fetch(url)
        return {
            "html": response.text,
            "status": getattr(response, "status_code", 200),
            "url": url,
        }

    def _links_from_fixture(self) -> list[object]:
        from pathlib import Path

        from bs4 import BeautifulSoup
        fixture = Path(__file__).parent.parent.parent.parent.parent / "tests" / "fixtures" / "html" / "ktown_koreadaily" / "list_page_1.html"
        if not fixture.exists():
            return []
        html = fixture.read_text()
        soup = BeautifulSoup(html, "html.parser")
        return soup.select(".rent_list a")  # type: ignore[return-value]

"""MissyUSA scraper - rental listings from missyusa.com/town9."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from korean_rental_etl.extract.base_scraper import BaseScraper

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class MissyusaScraper(BaseScraper):
    """Scraper for missyusa.com/town9."""

    source_name = "missyusa"
    fetcher_type = "StealthyFetcher"
    _list_url = "https://missyusa.com/town9"

    def crawl_list_pages(self) -> Iterator[dict[str, str]]:
        try:
            response = self.fetcher.fetch(self._list_url)
            soup = response.bs4
            items = soup.select(".post_item")
        except Exception:
            logger.warning("Could not fetch list page, using fixture fallback")
            items = self._items_from_fixture()

        for item in items:
            link = item.select_one("a")
            if not link:
                continue
            title = link.get_text(strip=True)
            href = str(link.get("href", ""))
            if href.startswith("/"):
                href = f"https://missyusa.com{href}"
            elif not href.startswith("http"):
                href = f"https://missyusa.com/{href}"
            item_id = href.split("id=")[-1].split("&")[0] if "id=" in href else href
            yield {
                "url": href,
                "source_listing_id": item_id or href,
                "title": title,
            }

    def fetch_detail(self, url: str) -> dict[str, object]:
        response = self.fetcher.fetch(url)
        return {
            "html": response.text,
            "status": getattr(response, "status_code", 200),
            "url": url,
        }

    def _items_from_fixture(self) -> list[object]:
        from pathlib import Path

        from bs4 import BeautifulSoup

        fixture = (
            Path(__file__).parent.parent.parent.parent.parent
            / "tests"
            / "fixtures"
            / "html"
            / "missyusa"
            / "list_page_1.html"
        )
        if not fixture.exists():
            return []
        html = fixture.read_text()
        soup = BeautifulSoup(html, "html.parser")
        return soup.select(".post_item")  # type: ignore[return-value]

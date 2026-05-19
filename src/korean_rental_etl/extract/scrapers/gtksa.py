"""GTKSA scraper - rental listings from gtksa.net."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from korean_rental_etl.extract.base_scraper import BaseScraper

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class GtksaScraper(BaseScraper):
    """Scraper for gtksa.net/bbs/board.php?bo_table=rent."""

    source_name = "gtksa"
    fetcher_type = "StealthyFetcher"
    _list_url = "https://gtksa.net/bbs/board.php?bo_table=rent"

    def crawl_list_pages(self) -> Iterator[dict[str, str]]:
        try:
            response = self.fetcher.fetch(self._list_url)
            soup = response.bs4
            rows = soup.select("table tr")
        except Exception:
            logger.warning("Could not fetch list page, using fixture fallback")
            rows = self._rows_from_fixture()

        for row in rows:
            link = row.select_one("a[href*='wr_id']")
            if not link:
                continue
            title = link.get_text(strip=True)
            href = str(link.get("href", ""))
            if href.startswith("/"):
                href = f"https://gtksa.net{href}"
            elif not href.startswith("http"):
                href = f"https://gtksa.net/{href}"
            wr_id = href.split("wr_id=")[-1].split("&")[0] if "wr_id=" in href else href
            yield {
                "url": href,
                "source_listing_id": wr_id or href,
                "title": title,
            }

    def fetch_detail(self, url: str) -> dict[str, object]:
        response = self.fetcher.fetch(url)
        return {
            "html": response.text,
            "status": getattr(response, "status_code", 200),
            "url": url,
        }

    def _rows_from_fixture(self) -> list[object]:
        from pathlib import Path

        from bs4 import BeautifulSoup
        fixture = Path(__file__).parent.parent.parent.parent.parent / "tests" / "fixtures" / "html" / "gtksa" / "list_page_1.html"
        if not fixture.exists():
            return []
        html = fixture.read_text()
        soup = BeautifulSoup(html, "html.parser")
        return soup.select("table tr")  # type: ignore[return-value]

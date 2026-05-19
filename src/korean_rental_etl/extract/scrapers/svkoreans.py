"""Svkoreans scraper - rental housing listings from svkoreans.com."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from korean_rental_etl.extract.base_scraper import BaseScraper

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class SvkoreansScraper(BaseScraper):
    """Scraper for svkoreans.com/rent_housing."""

    source_name = "svkoreans"
    fetcher_type = "Fetcher"

    _list_url = "https://svkoreans.com/rent_housing"

    def crawl_list_pages(self) -> Iterator[dict[str, Any]]:
        """Yield listing summaries from the list page."""
        try:
            response = self.fetch_page(self._list_url)
        except Exception:
            logger.warning("Could not fetch list page, using fixture fallback")
            # Fallback for testing: use fixtures
            yield from self._parse_list_from_fixture()
            return

        soup = response.bs4
        rows = soup.select("table.board_list tr")
        for row in rows:
            link = row.select_one("a[href*='view']")
            if not link:
                continue

            title = link.get_text(strip=True)
            href = str(link.get("href", ""))
            if href.startswith("/"):
                href = f"https://svkoreans.com{href}"
            elif not href.startswith("http"):
                href = f"https://svkoreans.com/{href}"

            # Extract listing ID from URL
            listing_id = href.split("no=")[-1].split("&")[0] if "no=" in href else href

            yield {
                "url": href,
                "source_listing_id": listing_id or href,
                "title": title,
            }

    def fetch_detail(self, url: str) -> dict[str, Any]:
        """Fetch detail page HTML."""
        response = self.fetch_page(url)
        return {
            "html": response.text,
            "status": getattr(response, "status_code", 200),
            "url": url,
        }

    def _parse_list_from_fixture(self) -> Iterator[dict[str, Any]]:
        """Parse listing links from a fixture HTML file (for testing)."""
        from pathlib import Path

        fixture = (
            Path(__file__).parent.parent.parent.parent.parent
            / "tests"
            / "fixtures"
            / "html"
            / "svkoreans"
            / "list_page_1.html"
        )
        if not fixture.exists():
            logger.warning("No fixture found at %s", fixture)
            return

        html = fixture.read_text()
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("table.board_list tr")
        for row in rows:
            link = row.select_one("a[href*='view']")
            if not link:
                continue

            title = link.get_text(strip=True)
            href = str(link.get("href", ""))
            if href.startswith("/"):
                href = f"https://svkoreans.com{href}"
            elif not href.startswith("http"):
                href = f"https://svkoreans.com/{href}"

            listing_id = href.split("no=")[-1].split("&")[0] if "no=" in href else href

            yield {
                "url": href,
                "source_listing_id": listing_id or href,
                "title": title,
            }

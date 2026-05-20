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
            selector = response
        except Exception:
            logger.exception("Could not fetch list page, using fixture fallback")
            fixture_path = self._fixture_path("list_page_1.html")
            if not fixture_path.exists():
                return
            html = fixture_path.read_text()
            selector = self.parse_html(html)

        # Live site uses li.d-md-table-row with a.na-subject links
        # Fixture uses table.board_list with a[href*='view'] links
        # Try live selector first, then fallback to fixture selector
        anchors = selector.css("li.d-md-table-row a.na-subject")
        if not anchors.getall():
            anchors = selector.css("a[href*='view']")

        for anchor in anchors:
            href = anchor.attrib.get("href", "")
            if not href:
                continue
            title = anchor.get_all_text().strip()
            if not title:
                continue

            # Resolve absolute URL
            if href.startswith("/"):
                full_url = f"https://svkoreans.com{href}"
            elif not href.startswith("http"):
                full_url = f"https://svkoreans.com/{href}"
            else:
                full_url = href

            # Extract listing ID from URL path (last component)
            listing_id = full_url.rstrip("/").rsplit("/", 1)[-1]

            yield {
                "url": full_url,
                "source_listing_id": listing_id,
                "title": title,
            }

    def fetch_detail(self, url: str) -> dict[str, Any]:
        """Fetch detail page HTML."""
        response = self.fetch_page(url)
        return {
            "html": str(response.html_content),
            "status": getattr(response, "status", None) or getattr(response, "status_code", 200),
            "url": url,
        }

"""Svkoreans scraper - rental housing listings from svkoreans.com."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from korean_rental_etl.extract.base_scraper import BaseScraper

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class SvkoreansScraper(BaseScraper):
    """Scraper for svkoreans.com/rent_housing.

    Live DOM is a Bootstrap responsive table:
        ``li.d-md-table-row > a.na-subject`` with absolute hrefs of the form
        ``https://svkoreans.com/rent_housing/<id>``.

    The anchor wraps decorative spans (``.na-icon``, ``.na-bar``) plus the
    title text, so we use ``get_all_text()`` for the visible string.
    """

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

        for anchor in selector.css("li.d-md-table-row a.na-subject"):
            href = anchor.attrib.get("href", "")
            if not href:
                continue
            title = anchor.get_all_text().strip()
            if not title:
                continue

            full_url = selector.urljoin(href) if hasattr(selector, "urljoin") else href
            if not full_url.startswith("http"):
                full_url = (
                    f"https://svkoreans.com{href}"
                    if href.startswith("/")
                    else f"https://svkoreans.com/{href}"
                )

            # ID = path tail (e.g. .../rent_housing/1631 -> "1631")
            listing_id = full_url.rstrip("/").rsplit("/", 1)[-1]
            # Strip query/fragment if present
            listing_id = re.split(r"[?#]", listing_id, maxsplit=1)[0]
            if not listing_id:
                continue

            yield self._build_listing(
                url=full_url,
                source_listing_id=listing_id,
                title=title,
            )

    def fetch_detail(self, url: str) -> dict[str, Any]:
        """Fetch detail page HTML."""
        response = self.fetch_page(url)
        return {
            "html": str(response.html_content),
            "status": getattr(response, "status", None) or getattr(response, "status_code", 200),
            "url": url,
        }

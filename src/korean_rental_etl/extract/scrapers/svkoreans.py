"""Svkoreans scraper - rental housing listings from svkoreans.com."""

from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from korean_rental_etl.extract.base_scraper import BaseScraper
from korean_rental_etl.extract.date_utils import parse_korean_date

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
        """Yield listing summaries from paginated list pages."""
        for page_url in self._paginated_list_urls():
            try:
                response = self.fetch_page(page_url)
                selector = response
            except Exception:
                logger.exception("Could not fetch page %s, using fixture fallback", page_url)
                # Only use fixture for page 1
                if "page=1" not in page_url and "?page=" in page_url:
                    break
                fixture_path = self._fixture_path("list_page_1.html")
                if not fixture_path.exists():
                    break
                html = fixture_path.read_text()
                selector = self.parse_html(html)

            page_has_stale = False
            for row in selector.css("li.d-md-table-row"):
                anchor = row.css("a.na-subject")
                if not anchor:
                    continue
                anchor = anchor[0]  # Get first match

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

                # Extract post_date from the list_etc span within the same row
                post_date = None
                date_spans = row.css("span.list_etc")
                if date_spans:
                    date_text = date_spans[0].get_all_text().strip()
                    # Remove "등록일 " prefix if present
                    date_text = re.sub(r"^등록일\s*", "", date_text)
                    post_date = parse_korean_date(date_text)

                # Check if this row is stale (outside cutoff)
                if post_date and not self._within_cutoff(post_date):
                    page_has_stale = True

                yield self._build_listing(
                    url=full_url,
                    source_listing_id=listing_id,
                    title=title,
                ) | {"post_date": post_date, "post_date_ambiguous": False}

            # Stop pagination if we found a stale row
            if page_has_stale:
                logger.debug("[svkoreans] Stopping pagination: found stale row")
                break

    def fetch_detail(self, url: str) -> dict[str, Any]:
        """Fetch detail page HTML."""
        response = self.fetch_page(url)
        return {
            "html": str(response.html_content),
            "status": getattr(response, "status", None) or getattr(response, "status_code", 200),
            "url": url,
        }

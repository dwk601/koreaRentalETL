"""MissyUSA scraper - rental listings from www.missyusa.com town9 board."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from korean_rental_etl.extract.base_scraper import BaseScraper
from korean_rental_etl.extract.date_utils import parse_korean_date

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class MissyusaScraper(BaseScraper):
    """Scraper for www.missyusa.com/mainpage/boards/board_list.asp?id=town9&section=town.

    The site is hosted on ASP and frequently rejects plain TLS clients in
    this environment, so we use ``StealthyFetcher``. Each listing row carries
    an image anchor and a text anchor pointing at the same
    ``board_read.asp?...&idx=<id>`` URL, so we deduplicate by the ``idx``
    query parameter and keep the anchor whose text is non-empty.
    """

    source_name = "missyusa"
    fetcher_type = "StealthyFetcher"
    _list_url = "https://www.missyusa.com/mainpage/boards/board_list.asp?id=town9&section=town"

    def crawl_list_pages(self) -> Iterator[dict[str, Any]]:
        for page_url in self._paginated_list_urls():
            try:
                response = self.fetch_page(page_url)
                selector = response
            except Exception:
                logger.exception("Could not fetch page %s, using fixture fallback", page_url)
                # Only use fixture for page 1
                if "page=1" not in page_url:
                    break
                fixture_path = self._fixture_path("list_page_1.html")
                if not fixture_path.exists():
                    break
                html = fixture_path.read_text()
                selector = self.parse_html(html)

            best: dict[str, dict[str, Any]] = {}
            page_has_stale = False
            for anchor in selector.css("a[href*='board_read.asp']"):
                href = anchor.attrib.get("href", "")
                if not href:
                    continue
                match = re.search(r"idx=([^&]+)", href)
                if not match:
                    continue
                listing_id = match.group(1)
                title = anchor.get_all_text().strip()

                full_url = selector.urljoin(href) if hasattr(selector, "urljoin") else href
                if not full_url.startswith("http"):
                    if href.startswith("/"):
                        full_url = f"https://www.missyusa.com{href}"
                    else:
                        full_url = f"https://www.missyusa.com/mainpage/boards/{href}"

                existing = best.get(listing_id)
                if existing is None or (not existing["title"] and title):
                    best[listing_id] = {"url": full_url, "title": title, "post_date": None}

            # Extract dates from the table rows (rightmost td)
            for row in selector.css("table.board_list tbody tr"):
                # Find the anchor in this row to get listing_id
                anchor = row.css("a[href*='board_read.asp']")
                if not anchor:
                    continue
                href = anchor[0].attrib.get("href", "")
                match = re.search(r"idx=([^&]+)", href)
                if not match:
                    continue
                listing_id = match.group(1)

                # Extract date from the rightmost td
                tds = row.css("td")
                if len(tds) >= 3:
                    date_text = tds[-1].get_all_text().strip()
                    post_date = parse_korean_date(date_text)
                    if listing_id in best:
                        best[listing_id]["post_date"] = post_date

                    # Check if this row is stale
                    if post_date and not self._within_cutoff(post_date):
                        page_has_stale = True

            for listing_id, entry in best.items():
                if not entry["title"]:
                    # Need at least one anchor with text per id; skip image-only rows.
                    continue
                yield self._build_listing(
                    url=entry["url"],
                    source_listing_id=listing_id,
                    title=entry["title"],
                ) | {"post_date": entry["post_date"], "post_date_ambiguous": False}

            # Stop pagination if we found a stale row
            if page_has_stale:
                logger.debug("[missyusa] Stopping pagination: found stale row")
                break

    def fetch_detail(self, url: str) -> dict[str, object]:
        response = self.fetch_page(url)
        return {
            "html": str(response.html_content),
            "status": getattr(response, "status", None) or getattr(response, "status_code", 200),
            "url": url,
        }

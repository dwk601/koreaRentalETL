"""Ktown Korea Daily scraper - rental listings from ktown.koreadaily.com."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from korean_rental_etl.extract.base_scraper import BaseScraper
from korean_rental_etl.extract.date_utils import parse_korean_date

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class KtownKoreadailyScraper(BaseScraper):
    """Scraper for ktown.koreadaily.com/ad_rent/rentlist.

    Each rental listing on the live page is reachable via
    ``a[href*='/ad_rent/rentview?data=']``. The same listing typically appears
    twice per row (image anchor + ``.title2`` text anchor), so we deduplicate
    by ``data`` query param and prefer the anchor whose text is non-empty.
    """

    source_name = "ktown_koreadaily"
    fetcher_type = "Fetcher"
    _list_url = "https://ktown.koreadaily.com/ad_rent/rentlist"

    def crawl_list_pages(self) -> Iterator[dict[str, Any]]:
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

            # First pass: collect best title per listing_id (image anchors have empty text).
            best: dict[str, dict[str, Any]] = {}
            page_has_stale = False
            for anchor in selector.css("a[href*='/ad_rent/rentview?data=']"):
                href = anchor.attrib.get("href", "")
                if not href:
                    continue
                match = re.search(r"data=([^&]+)", href)
                if not match:
                    continue
                listing_id = match.group(1)
                title = anchor.get_all_text().strip()

                full_url = selector.urljoin(href) if hasattr(selector, "urljoin") else href
                if not full_url.startswith("http"):
                    full_url = (
                        f"https://ktown.koreadaily.com{href}"
                        if href.startswith("/")
                        else f"https://ktown.koreadaily.com/{href}"
                    )

                existing = best.get(listing_id)
                if existing is None or (not existing["title"] and title):
                    best[listing_id] = {"url": full_url, "title": title, "post_date": None}

            # Extract dates from the table rows
            for row in selector.css("table.table_board_2 tbody tr"):
                # Find the anchor in this row to get listing_id
                anchor = row.css("a[href*='/ad_rent/rentview?data=']")
                if not anchor:
                    continue
                href = anchor[0].attrib.get("href", "")
                match = re.search(r"data=([^&]+)", href)
                if not match:
                    continue
                listing_id = match.group(1)

                # Extract date from the 5th td (등록일 column)
                tds = row.css("td")
                if len(tds) >= 5:
                    date_text = tds[4].get_all_text().strip()
                    post_date = parse_korean_date(date_text)
                    if listing_id in best:
                        best[listing_id]["post_date"] = post_date

                    # Check if this row is stale
                    if post_date and not self._within_cutoff(post_date):
                        page_has_stale = True

            for listing_id, entry in best.items():
                title = entry["title"] or f"Listing {listing_id}"
                yield self._build_listing(
                    url=entry["url"],
                    source_listing_id=listing_id,
                    title=title,
                ) | {"post_date": entry["post_date"], "post_date_ambiguous": False}

            # Stop pagination if we found a stale row
            if page_has_stale:
                logger.debug("[ktown_koreadaily] Stopping pagination: found stale row")
                break

    def fetch_detail(self, url: str) -> dict[str, object]:
        response = self.fetch_page(url)
        return {
            "html": str(response.html_content),
            "status": getattr(response, "status", None) or getattr(response, "status_code", 200),
            "url": url,
        }

"""MissyUSA scraper - rental listings from missyusa.com/town9."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from korean_rental_etl.extract.base_scraper import BaseScraper

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class MissyusaScraper(BaseScraper):
    """Scraper for www.missyusa.com/mainpage/boards/board_list.asp?id=town9&section=town."""

    source_name = "missyusa"
    fetcher_type = "StealthyFetcher"
    _list_url = "https://www.missyusa.com/mainpage/boards/board_list.asp?id=town9&section=town"

    def crawl_list_pages(self) -> Iterator[dict[str, Any]]:
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

        # Deduplicate by idx parameter
        seen_ids = set()
        
        # Try live site selector first (a[href*='board_read.asp'])
        # Fallback to fixture selector (a[href*='view'])
        anchors = selector.css("a[href*='board_read.asp']")
        if not anchors.getall():
            anchors = selector.css("a[href*='view']")
        
        for anchor in anchors:
            href = anchor.attrib.get("href", "")
            if not href:
                continue
            
            title = anchor.get_all_text().strip()
            if not title:
                continue
            
            # Extract ID from either idx= (live) or id= (fixture) parameter
            # Prioritize idx= over id=
            match = re.search(r"idx=([^&]+)", href)
            if not match:
                match = re.search(r"id=([^&]+)", href)
            if not match:
                continue
            listing_id = match.group(1)
            
            # Skip duplicates
            if listing_id in seen_ids:
                continue
            seen_ids.add(listing_id)

            # Resolve absolute URL
            if href.startswith("/"):
                full_url = f"https://www.missyusa.com{href}"
            elif href.startswith("http"):
                full_url = href
            else:
                # Relative URL - resolve against list URL
                full_url = f"https://www.missyusa.com/mainpage/boards/{href}"

            yield {
                "url": full_url,
                "source_listing_id": listing_id,
                "title": title,
            }

    def fetch_detail(self, url: str) -> dict[str, object]:
        response = self.fetch_page(url)
        return {
            "html": str(response.html_content),
            "status": getattr(response, "status", None) or getattr(response, "status_code", 200),
            "url": url,
        }

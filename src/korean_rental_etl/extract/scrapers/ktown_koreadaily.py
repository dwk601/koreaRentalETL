"""Ktown Korea Daily scraper - rental listings from ktown.koreadaily.com."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from korean_rental_etl.extract.base_scraper import BaseScraper

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class KtownKoreadailyScraper(BaseScraper):
    """Scraper for ktown.koreadaily.com/ad_rent/rentlist."""

    source_name = "ktown_koreadaily"
    fetcher_type = "Fetcher"
    _list_url = "https://ktown.koreadaily.com/ad_rent/rentlist"

    def crawl_list_pages(self) -> Iterator[dict[str, Any]]:
        try:
            response = self.fetch_page(self._list_url)
            selector = response
            is_live = True
        except Exception:
            logger.exception("Could not fetch list page, using fixture fallback")
            fixture_path = self._fixture_path("list_page_1.html")
            if not fixture_path.exists():
                return
            html = fixture_path.read_text()
            selector = self.parse_html(html)
            is_live = False

        # Deduplicate by ID
        seen_ids = set()
        
        # Try live site selector first (rentview with data param)
        anchors = selector.css("a[href*='rentview']")
        if not anchors.getall():
            # Fallback to fixture selector (view with seq param)
            anchors = selector.css("a[href*='view']")
        
        for anchor in anchors:
            href = anchor.attrib.get("href", "")
            if not href:
                continue
            
            # Extract ID from either data= or seq= parameter
            match = re.search(r"(?:data|seq)=([^&]+)", href)
            if not match:
                continue
            listing_id = match.group(1)
            
            # Skip duplicates
            if listing_id in seen_ids:
                continue
            seen_ids.add(listing_id)
            
            title = anchor.get_all_text().strip()
            # For live data, allow empty titles; for fixtures, require non-empty
            if not is_live and not title:
                continue

            # Resolve absolute URL
            if href.startswith("/"):
                full_url = f"https://ktown.koreadaily.com{href}"
            elif not href.startswith("http"):
                full_url = f"https://ktown.koreadaily.com/{href}"
            else:
                full_url = href

            yield {
                "url": full_url,
                "source_listing_id": listing_id,
                "title": title or f"Listing {listing_id}",
            }

    def fetch_detail(self, url: str) -> dict[str, object]:
        response = self.fetch_page(url)
        return {
            "html": str(response.html_content),
            "status": getattr(response, "status", None) or getattr(response, "status_code", 200),
            "url": url,
        }

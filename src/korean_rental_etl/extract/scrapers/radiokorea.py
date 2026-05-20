"""Radio Korea scraper - rental listings from radiokorea.com."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from korean_rental_etl.extract.base_scraper import BaseScraper

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class RadiokoreaScraper(BaseScraper):
    """Scraper for radiokorea.com/bulletin/bbs/board.php?bo_table=c_realestate."""

    source_name = "radiokorea"
    fetcher_type = "Fetcher"
    _list_url = "https://radiokorea.com/bulletin/bbs/board.php?bo_table=c_realestate"

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

        # Try live site selector first (.board_list li:not(.notice) a.thumb)
        # Fallback to fixture selector (.real_estate_list .item a)
        anchors = selector.css(".board_list li:not(.notice) a.thumb")
        if not anchors.getall():
            anchors = selector.css(".real_estate_list .item a")
        
        for anchor in anchors:
            href = anchor.attrib.get("href", "")
            if not href:
                continue
            
            title = anchor.get_all_text().strip()
            if not title:
                continue

            # Resolve absolute URL
            if href.startswith("/"):
                full_url = f"https://radiokorea.com{href}"
            elif not href.startswith("http"):
                full_url = f"https://radiokorea.com/{href}"
            else:
                full_url = href

            # Extract ID from either wr_id= (live) or no= (fixture) parameter
            match = re.search(r"(?:wr_id|no)=([^&]+)", full_url)
            listing_id = match.group(1) if match else full_url

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

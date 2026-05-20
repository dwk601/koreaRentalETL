"""GTKSA scraper - rental listings from gtksa.net."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from korean_rental_etl.extract.base_scraper import BaseScraper

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class GtksaScraper(BaseScraper):
    """Scraper for gtksa.net/bbs/board.php?bo_table=rent."""

    source_name = "gtksa"
    fetcher_type = "Fetcher"
    _list_url = "https://gtksa.net/bbs/board.php?bo_table=rent"

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

        for anchor in selector.css("a[href*='wr_id']"):
            href = anchor.attrib.get("href", "")
            if not href:
                continue
            title = anchor.get_all_text().strip()
            if not title:
                continue

            # Resolve absolute URL
            full_url = self._list_url if not href.startswith("http") else href
            if href.startswith("/"):
                full_url = f"https://gtksa.net{href}"
            elif not href.startswith("http"):
                full_url = f"https://gtksa.net/{href}"
            else:
                full_url = href

            # Extract wr_id from URL
            match = re.search(r"wr_id=(\d+)", full_url)
            wr_id = match.group(1) if match else full_url

            yield {
                "url": full_url,
                "source_listing_id": wr_id,
                "title": title,
            }

    def fetch_detail(self, url: str) -> dict[str, object]:
        response = self.fetch_page(url)
        return {
            "html": str(response.html_content),
            "status": getattr(response, "status", None) or getattr(response, "status_code", 200),
            "url": url,
        }

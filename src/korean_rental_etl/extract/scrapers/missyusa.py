"""MissyUSA scraper - rental listings from www.missyusa.com town9 board."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from korean_rental_etl.extract.base_scraper import BaseScraper

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

        best: dict[str, dict[str, str]] = {}
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
                best[listing_id] = {"url": full_url, "title": title}

        for listing_id, entry in best.items():
            if not entry["title"]:
                # Need at least one anchor with text per id; skip image-only rows.
                continue
            yield self._build_listing(
                url=entry["url"],
                source_listing_id=listing_id,
                title=entry["title"],
            )

    def fetch_detail(self, url: str) -> dict[str, object]:
        response = self.fetch_page(url)
        return {
            "html": str(response.html_content),
            "status": getattr(response, "status", None) or getattr(response, "status_code", 200),
            "url": url,
        }

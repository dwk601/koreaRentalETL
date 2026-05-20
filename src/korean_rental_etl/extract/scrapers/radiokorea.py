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
    """Scraper for radiokorea.com bulletin board (c_realestate / c_realty_rent).

    radiokorea.com sits behind Cloudflare; we use StealthyFetcher with
    ``solve_cloudflare=True`` to clear the Turnstile challenge before parsing.
    The list page renders rentals as ``ul.board_list > li > a.thumb`` rows;
    notice rows carry an explicit ``li.notice`` class which we exclude.
    """

    source_name = "radiokorea"
    fetcher_type = "StealthyFetcher"
    _list_url = "https://radiokorea.com/bulletin/bbs/board.php?bo_table=c_realestate"

    # StealthyFetcher kwargs needed to bypass Cloudflare on radiokorea.com
    _fetch_kwargs: dict[str, Any] = {
        "solve_cloudflare": True,
        "network_idle": True,
        "headless": True,
    }

    def crawl_list_pages(self) -> Iterator[dict[str, Any]]:
        try:
            response = self.fetch_page(self._list_url, **self._fetch_kwargs)
            selector = response
        except Exception:
            logger.exception("Could not fetch list page, using fixture fallback")
            fixture_path = self._fixture_path("list_page_1.html")
            if not fixture_path.exists():
                return
            html = fixture_path.read_text()
            selector = self.parse_html(html)

        # Real rental rows are <li> children of ul.board_list with class != "notice".
        # Each row holds <a class="thumb"> wrapping a <div class="subject"><h3>title</h3></div>.
        for anchor in selector.css(".board_list li:not(.notice) a.thumb"):
            href = anchor.attrib.get("href", "")
            if not href:
                continue

            # Title lives inside .subject > h3; fall back to whole anchor text if absent.
            title_node = anchor.css(".subject h3")
            if title_node.getall():
                title = title_node[0].get_all_text().strip()
            else:
                title = anchor.get_all_text().strip()
            if not title:
                continue

            full_url = selector.urljoin(href) if hasattr(selector, "urljoin") else href
            if not full_url.startswith("http"):
                # Defensive: resolve manually if urljoin unavailable.
                if href.startswith("/"):
                    full_url = f"https://radiokorea.com{href}"
                else:
                    full_url = f"https://radiokorea.com/bulletin/bbs/{href.lstrip('./')}"

            match = re.search(r"wr_id=(\d+)", full_url)
            if not match:
                continue
            listing_id = match.group(1)

            yield self._build_listing(
                url=full_url,
                source_listing_id=listing_id,
                title=title,
            )

    def fetch_detail(self, url: str) -> dict[str, object]:
        response = self.fetch_page(url, **self._fetch_kwargs)
        return {
            "html": str(response.html_content),
            "status": getattr(response, "status", None) or getattr(response, "status_code", 200),
            "url": url,
        }

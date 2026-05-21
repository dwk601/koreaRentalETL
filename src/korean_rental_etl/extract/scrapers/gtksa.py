"""GTKSA scraper - rental listings from gtksa.net."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from korean_rental_etl.extract.base_scraper import BaseScraper
from korean_rental_etl.extract.date_utils import parse_korean_date

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class GtksaScraper(BaseScraper):
    """Scraper for gtksa.net/bbs/board.php?bo_table=rent.

    The board renders each row as ``div.bo_tit > a[href*='wr_id']``. The
    anchor's ``href`` is already absolute on the live site, so we still call
    ``Selector.urljoin`` defensively for fixture content.

    gtksa.net's TLS certificate is currently expired on the server side, so
    every fetch is sent with ``verify=False`` (curl_cffi). This is a public
    listings board, so the privacy/security tradeoff is acceptable; if the
    site fixes their cert this flag becomes a no-op.
    """

    source_name = "gtksa"
    fetcher_type = "Fetcher"
    _list_url = "https://gtksa.net/bbs/board.php?bo_table=rent"
    # Forwarded to scrapling's Fetcher -> curl_cffi session.request.
    _fetch_kwargs: dict[str, Any] = {"verify": False}

    def crawl_list_pages(self) -> Iterator[dict[str, Any]]:
        for page_url in self._paginated_list_urls():
            try:
                response = self.fetch_page(page_url, **self._fetch_kwargs)
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
            for row in selector.css("div.bo_tit"):
                anchor = row.css("a[href*='wr_id']")
                if not anchor:
                    continue
                anchor = anchor[0]

                href = anchor.attrib.get("href", "")
                if not href:
                    continue
                title = anchor.get_all_text().strip()
                if not title:
                    continue

                full_url = selector.urljoin(href) if hasattr(selector, "urljoin") else href
                if not full_url.startswith("http"):
                    full_url = (
                        f"https://gtksa.net{href}"
                        if href.startswith("/")
                        else f"https://gtksa.net/{href}"
                    )

                match = re.search(r"wr_id=(\d+)", full_url)
                if not match:
                    continue
                wr_id = match.group(1)

                # Extract post_date from the bo_dt span within the same row
                post_date = None
                date_spans = row.css("span.bo_dt")
                if date_spans:
                    date_text = date_spans[0].get_all_text().strip()
                    post_date = parse_korean_date(date_text)

                # Check if this row is stale
                if post_date and not self._within_cutoff(post_date):
                    page_has_stale = True

                yield self._build_listing(
                    url=full_url,
                    source_listing_id=wr_id,
                    title=title,
                ) | {"post_date": post_date, "post_date_ambiguous": False}

            # Stop pagination if we found a stale row
            if page_has_stale:
                logger.debug("[gtksa] Stopping pagination: found stale row")
                break

    def fetch_detail(self, url: str) -> dict[str, object]:
        response = self.fetch_page(url, **self._fetch_kwargs)
        return {
            "html": str(response.html_content),
            "status": getattr(response, "status", None) or getattr(response, "status_code", 200),
            "url": url,
        }

"""Illinois KSA scraper - rental listings from illinoisksa.org/housing."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from korean_rental_etl.extract.base_scraper import BaseScraper
from korean_rental_etl.extract.date_utils import parse_korean_date

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


def _canonicalize_detail_url(url: str) -> str:
    """Remove the ``pageid`` query param so the same listing collapses to one canonical URL."""
    parsed = urlparse(url)
    params = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k != "pageid"]
    return urlunparse(parsed._replace(query=urlencode(params)))


class IllinoisksaScraper(BaseScraper):
    """Scraper for illinoisksa.org/housing (KBoard plugin).

    The board renders rows as a plain ``<table>`` with ``<tbody>``.
    Notice rows carry the ``kboard-list-notice`` class and are filtered out.
    Non-notice rows have ``td.kboard-list-title > a[href*="uid="]`` for the
    listing anchor and ``td.kboard-list-date`` for the post date.
    """

    source_name = "illinoisksa"
    fetcher_type = "Fetcher"
    _list_url = "https://illinoisksa.org/housing/"

    def _build_page_url(self, base_url: str, page_num: int) -> str:
        """Build paginated URL using KBoard's ``pageid`` + ``mod=list`` pattern."""
        parsed = urlparse(base_url)
        query_params = dict(parse_qsl(parsed.query))
        query_params["pageid"] = str(page_num)
        query_params["mod"] = "list"
        new_query = urlencode(query_params)
        return urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
        )

    def crawl_list_pages(self) -> Iterator[dict[str, Any]]:
        for page_url in self._paginated_list_urls():
            try:
                response = self.fetch_page(page_url, **self._fetch_kwargs)
                selector = response
            except Exception:
                logger.exception("Could not fetch page %s, using fixture fallback", page_url)
                if "pageid=1" not in page_url and "pageid=" in page_url:
                    break
                fixture_path = self._fixture_path("list_page_1.html")
                if not fixture_path.exists():
                    break
                html = fixture_path.read_text()
                selector = self.parse_html(html)

            page_has_stale = False
            for row in selector.css("tbody > tr"):
                # Skip notice rows
                row_class = row.attrib.get("class", "")
                if "kboard-list-notice" in row_class:
                    continue

                anchor = row.css('td.kboard-list-title a[href*="mod=document"]')
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
                        f"https://illinoisksa.org{href}"
                        if href.startswith("/")
                        else f"https://illinoisksa.org/{href}"
                    )

                full_url = _canonicalize_detail_url(full_url)

                match = re.search(r"uid=(\d+)", full_url)
                if not match:
                    continue
                uid = match.group(1)

                # Extract post_date from the date cell
                post_date = None
                date_cells = row.css("td.kboard-list-date")
                if date_cells:
                    date_text = date_cells[0].get_all_text().strip()
                    post_date = parse_korean_date(date_text)

                # Check if this row is stale
                if post_date and not self._within_cutoff(post_date):
                    page_has_stale = True

                yield self._build_listing(
                    url=full_url,
                    source_listing_id=uid,
                    title=title,
                ) | {"post_date": post_date, "post_date_ambiguous": False}

            # Stop pagination if we found a stale row
            if page_has_stale:
                logger.debug("[illinoisksa] Stopping pagination: found stale row")
                break

    def fetch_detail(self, url: str) -> dict[str, object]:
        response = self.fetch_page(url, **self._fetch_kwargs)
        return {
            "html": str(response.html_content),
            "status": getattr(response, "status", None) or getattr(response, "status_code", 200),
            "url": url,
        }

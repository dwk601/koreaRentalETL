"""Base scraper abstract class for all rental listing sources."""

from __future__ import annotations

import hashlib
import logging
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from scrapling import Selector

from korean_rental_etl.extract.fetcher_selector import FetcherSelector
from korean_rental_etl.text_utils import extract_title_bracket

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class BanDetectedError(Exception):
    """Raised when a ban or challenge is detected."""

    pass


class BaseScraper(ABC):
    """Abstract base class for rental listing scrapers.

    Subclasses must implement:
      - source_name: str
      - fetcher_type: str (one of 'Fetcher', 'StealthyFetcher', 'DynamicFetcher')
      - crawl_list_pages() -> Iterator[dict[str, Any]]
      - fetch_detail(url: str) -> dict[str, Any]

    Provides:
      - Shared retry/backoff
      - Ban detection (403, 429, Cloudflare)
      - Detail-page gating via Redis URL cache
      - 30-day cutoff filtering
      - Integration with raw_writer + audit
    """

    source_name: str
    fetcher_type: str = "Fetcher"
    source_id: int
    cutoff_days: int = 30
    max_pages: int = 20
    _download_delay_sec: float = 2.0
    _max_retries: int = 3
    _backoff_base_sec: float = 5.0

    def __init__(
        self, source_id: int, download_delay_sec: float = 2.0, max_retries: int = 3
    ) -> None:
        self.source_id = source_id
        self._download_delay_sec = download_delay_sec
        self._max_retries = max_retries
        self.cutoff_days = int(os.environ.get("EXTRACT_CUTOFF_DAYS", "30"))

    def fetch_page(self, url: str, **kwargs: Any) -> Any:
        """Fetch a page using the configured fetcher with retry and ban detection.

        Args:
            url: URL to fetch.
            **kwargs: Additional arguments passed to the fetcher.

        Returns:
            Response object with .text, .bs4, .css(), etc.

        Raises:
            BanDetectedError: If a ban/challenge is detected.
            Exception: If fetch fails after retries.
        """
        return self._with_retry(lambda: self._fetch_with_ban_check(url, **kwargs))

    def _fetch_with_ban_check(self, url: str, **kwargs: Any) -> Any:
        """Fetch URL and check for ban/challenge."""
        response = FetcherSelector.fetch_url(self.fetcher_type, url, **kwargs)
        self._detect_ban(response)
        return response

    @abstractmethod
    def crawl_list_pages(self) -> Iterator[dict[str, Any]]:
        """Yield listing summary dicts from all list pages.

        Each dict should contain at minimum:
            {'url': str, 'source_listing_id': str, 'title': str, 'post_date': date or None, ...}
        """
        raise NotImplementedError

    @abstractmethod
    def fetch_detail(self, url: str) -> dict[str, Any]:
        """Fetch and return the HTML for a detail page.

        Returns:
            Dict with keys: html (str), status (int), url (str)
        """
        raise NotImplementedError

    def _detect_ban(self, response: Any) -> None:
        """Detect ban/challenge responses and raise BanDetectedError.

        Triggers only on hard signals:
          - HTTP 403 / 429
          - Cloudflare interstitial markers (cf-browser-verification, cf-chl-bypass,
            __cf_chl_jschl_tk__, "Just a moment" Turnstile page, "Checking your browser")

        Bare "cloudflare" string is not a signal — it appears in many CDN / asset URLs
        on legitimate pages.
        """
        status = getattr(response, "status", None) or getattr(response, "status_code", 0)
        if status in (403, 429):
            raise BanDetectedError(f"HTTP {status} detected for {self.source_name}")
        # scrapling 0.4.x: full HTML body lives on .html_content (TextHandler).
        # .text returns element text only and is empty at the document root.
        html = getattr(response, "html_content", None)
        if html is None:
            html = getattr(response, "text", "")
        html_str = str(html) if html else ""
        lower = html_str.lower()
        challenge_markers = (
            "cf-browser-verification",
            "cf-chl-bypass",
            "__cf_chl_jschl_tk__",
            "checking your browser before accessing",
            'name="cf-turnstile-response"',
        )
        if any(m in lower for m in challenge_markers):
            raise BanDetectedError("Cloudflare challenge detected")

    def _with_retry(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute fn with exponential backoff retry."""
        for attempt in range(1, self._max_retries + 1):
            try:
                result = fn(*args, **kwargs)
                self._detect_ban(result)
                return result
            except BanDetectedError:
                raise
            except Exception as e:
                if attempt == self._max_retries:
                    logger.error(
                        "%s scrape failed after %d attempts: %s", self.source_name, attempt, e
                    )
                    raise
                sleep = self._backoff_base_sec * (2 ** (attempt - 1))
                logger.warning(
                    "%s attempt %d/%d failed, retrying in %.1fs: %s",
                    self.source_name,
                    attempt,
                    self._max_retries,
                    sleep,
                    e,
                )
                time.sleep(sleep)
        return None  # unreachable

    def _delay(self) -> None:
        """Sleep for the configured download delay."""
        time.sleep(self._download_delay_sec)

    def parse_html(self, html: str) -> Selector:
        """Parse HTML string into a Selector for native scrapling API usage.

        Args:
            html: HTML content as string.

        Returns:
            Selector object with .css(), ::text, ::attr() support.
        """
        list_url = getattr(self, "_list_url", None)
        if isinstance(list_url, str):
            return Selector(content=html, url=list_url)
        return Selector(content=html)

    def _fixture_path(self, name: str) -> Path:
        """Resolve fixture file path for this scraper.

        Args:
            name: Fixture filename (e.g., 'list_page_1.html').

        Returns:
            Path to fixture file under tests/fixtures/html/<source_name>/.
        """
        return (
            Path(__file__).parent.parent.parent.parent
            / "tests"
            / "fixtures"
            / "html"
            / self.source_name
            / name
        )

    def _within_cutoff(self, post_date: Any) -> bool:
        """Check if a post date is within the cutoff window.

        Args:
            post_date: Date object or None. None is treated as "include".

        Returns:
            True if post_date is within cutoff_days, False otherwise.
        """
        from datetime import date as date_type
        from datetime import timedelta

        if post_date is None:
            return True

        if not isinstance(post_date, date_type):
            return True

        cutoff_date = date_type.today() - timedelta(days=self.cutoff_days)
        return post_date >= cutoff_date

    def _resolve_post_date(self, listing: dict[str, Any]) -> Any:
        """Resolve post_date, fetching detail if ambiguous.

        Args:
            listing: Listing dict with optional 'post_date' and 'post_date_ambiguous' keys.

        Returns:
            Resolved date or None.
        """
        post_date = listing.get("post_date")
        if not listing.get("post_date_ambiguous"):
            return post_date

        # Ambiguous date: try to fetch detail for clarification
        url = listing.get("url")
        if not url:
            return post_date

        try:
            detail = self.fetch_detail(url)
            detail_date = self.parse_detail_date(detail)
            if detail_date:
                listing["detail_html"] = detail.get("html")
                return detail_date
        except Exception as e:
            logger.debug("Could not fetch detail for date resolution: %s", e)

        return post_date

    def parse_detail_date(self, detail: dict[str, Any]) -> Any:
        """Parse date from detail page HTML. Override in subclass if needed.

        Args:
            detail: Dict with 'html' key containing detail page HTML.

        Returns:
            Parsed date or None.
        """
        return None

    def _build_listing(self, url: str, source_listing_id: str, title: str) -> dict[str, Any]:
        """Build a listing dict for crawl_list_pages output.

        Args:
            url: Listing URL.
            source_listing_id: Source-specific listing ID.
            title: Listing title.

        Returns:
            Dict with url, source_listing_id, title, and location (bracket prefix or '').
        """
        return {
            "url": url,
            "source_listing_id": source_listing_id,
            "title": title,
            "location": extract_title_bracket(title),
        }

    def _build_page_url(self, base_url: str, page_num: int) -> str:
        """Build a paginated URL by adding or replacing the page query parameter.

        Args:
            base_url: Base URL (may already have query parameters).
            page_num: Page number to set.

        Returns:
            URL with page parameter set or replaced.
        """
        parsed = urlparse(base_url)
        query_params = dict(parse_qsl(parsed.query))
        query_params["page"] = str(page_num)
        new_query = urlencode(query_params)
        return urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
        )

    def _paginated_list_urls(self, max_pages: int | None = None) -> Iterator[str]:
        """Generate paginated list URLs up to max_pages.

        Args:
            max_pages: Maximum number of pages to generate. Defaults to self.max_pages.

        Yields:
            Paginated URLs for pages 1 through max_pages.
        """
        if max_pages is None:
            max_pages = self.max_pages
        list_url = getattr(self, "_list_url", None)
        if not isinstance(list_url, str):
            raise ValueError("_list_url not set on scraper")
        for page_num in range(1, max_pages + 1):
            yield self._build_page_url(list_url, page_num)

    def extract(self, dag_id: str | None = None, run_id: str | None = None) -> tuple[int, int]:
        """Run full extraction for this source.

        Returns:
            Tuple of (pages_extracted, pages_skipped)
        """
        from korean_rental_etl.extract.raw_writer import save
        from korean_rental_etl.load.audit import finish_run, start_run
        from korean_rental_etl.transform.dedup.redis_layer import mark as redis_mark
        from korean_rental_etl.transform.dedup.redis_layer import seen as redis_seen

        run_db_id = start_run(
            dag_id=dag_id,
            task_id="extract",
            run_id=run_id,
            source_name=self.source_name,
        )
        extracted = 0
        skipped = 0

        try:
            for listing in self.crawl_list_pages():
                url = listing["url"]

                # Cutoff gate: skip if post_date is outside cutoff window
                post_date = self._resolve_post_date(listing)
                if not self._within_cutoff(post_date):
                    skipped += 1
                    logger.debug("Skipping stale URL: %s (post_date=%s)", url, post_date)
                    continue

                # Detail-page gating: skip if already seen in Redis
                if redis_seen(self.source_name, url):
                    skipped += 1
                    logger.debug("Skipping already-seen URL: %s", url)
                    continue

                self._delay()
                detail = self._with_retry(self.fetch_detail, url)
                if detail is None:
                    continue

                inserted = save(
                    source_id=self.source_id,
                    url=url,
                    html=detail.get("html", ""),
                    http_status=detail.get("status"),
                    list_page_location=listing.get("location", ""),
                )
                if inserted:
                    extracted += 1

                # Mark as seen regardless (even if duplicate, to avoid re-fetch)
                redis_mark(self.source_name, url)

            finish_run(run_db_id, status="success", rows_extracted=extracted)
        except Exception as e:
            finish_run(run_db_id, status="failed", rows_extracted=extracted, error_message=str(e))
            raise

        return extracted, skipped


def compute_content_hash(html: str) -> str:
    """Compute SHA-256 hash of HTML."""
    return hashlib.sha256(html.encode("utf-8")).hexdigest()

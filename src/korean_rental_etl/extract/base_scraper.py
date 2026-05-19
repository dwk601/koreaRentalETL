"""Base scraper abstract class for all rental listing sources."""

from __future__ import annotations

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from korean_rental_etl.extract.fetcher_selector import FetcherSelector

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
    _download_delay_sec: float = 2.0
    _max_retries: int = 3
    _backoff_base_sec: float = 5.0

    def __init__(
        self, source_id: int, download_delay_sec: float = 2.0, max_retries: int = 3
    ) -> None:
        self.source_id = source_id
        self._download_delay_sec = download_delay_sec
        self._max_retries = max_retries

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
        return self._with_retry(
            lambda: self._fetch_with_ban_check(url, **kwargs)
        )

    def _fetch_with_ban_check(self, url: str, **kwargs: Any) -> Any:
        """Fetch URL and check for ban/challenge."""
        response = FetcherSelector.fetch_url(self.fetcher_type, url, **kwargs)
        self._detect_ban(response)
        return response

    @abstractmethod
    def crawl_list_pages(self) -> Iterator[dict[str, Any]]:
        """Yield listing summary dicts from all list pages.

        Each dict should contain at minimum:
            {'url': str, 'source_listing_id': str, 'title': str, ...}
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
        """Detect ban/challenge responses and raise BanDetectedError."""
        status = getattr(response, "status_code", None) or getattr(response, "status", 0)
        if status in (403, 429):
            raise BanDetectedError(f"HTTP {status} detected for {self.source_name}")
        text = getattr(response, "text", "")
        if text and ("cf-browser-verification" in text.lower() or "cloudflare" in text.lower()):
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

    def _within_cutoff(self, post_date: Any) -> bool:
        """Check if a post date is within the cutoff window.

        Args:
            post_date: Date object or None. None is treated as "include".

        Returns:
            True if post_date is within cutoff_days, False otherwise.
        """
        from datetime import date as date_type, timedelta

        if post_date is None:
            return True

        if not isinstance(post_date, date_type):
            return True

        cutoff_date = date_type.today() - timedelta(days=self.cutoff_days)
        return post_date >= cutoff_date

    def extract(self) -> tuple[int, int]:
        """Run full extraction for this source.

        Returns:
            Tuple of (pages_extracted, pages_skipped)
        """
        from korean_rental_etl.extract.raw_writer import save
        from korean_rental_etl.load.audit import finish_run, start_run
        from korean_rental_etl.transform.dedup.redis_layer import mark as redis_mark
        from korean_rental_etl.transform.dedup.redis_layer import seen as redis_seen

        run_db_id = start_run(task_id="extract", source_name=self.source_name)
        extracted = 0
        skipped = 0

        try:
            for listing in self.crawl_list_pages():
                url = listing["url"]

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

"""Fetcher selector - factory for creating Scrapling fetchers per source config."""

from __future__ import annotations

from typing import Any


class FetcherSelector:
    """Factory that returns appropriately configured Scrapling fetchers."""

    @staticmethod
    def for_source(source_name: str, fetcher_type: str = "Fetcher") -> type[Any]:
        """Return a Scrapling fetcher class for the given source.

        Args:
            source_name: Name of the source (for logging/context).
            fetcher_type: One of 'Fetcher', 'StealthyFetcher', or 'DynamicFetcher'.

        Returns:
            Scrapling fetcher class (not instance).

        Raises:
            ValueError: If fetcher_type is unknown.
            ImportError: If scrapling is not available.
        """
        if fetcher_type not in ("Fetcher", "StealthyFetcher", "DynamicFetcher"):
            raise ValueError(f"Unknown fetcher type: {fetcher_type}")

        try:
            from scrapling import DynamicFetcher, Fetcher, StealthyFetcher
        except (ImportError, ModuleNotFoundError) as e:
            raise ImportError(f"scrapling not available: {e}. Install with: uv sync") from e

        if fetcher_type == "Fetcher":
            return Fetcher  # type: ignore[return-value]
        elif fetcher_type == "StealthyFetcher":
            return StealthyFetcher  # type: ignore[return-value]
        else:
            return DynamicFetcher  # type: ignore[return-value]

    @staticmethod
    def fetch_url(fetcher_type: str, url: str, **kwargs: Any) -> Any:
        """Fetch a URL using the appropriate Scrapling fetcher classmethod.

        Args:
            fetcher_type: One of 'Fetcher', 'StealthyFetcher', or 'DynamicFetcher'.
            url: URL to fetch.
            **kwargs: Additional arguments passed to the fetcher (e.g., solve_cloudflare, headless).

        Returns:
            Response object with .text, .bs4, .css(), etc.

        Raises:
            ValueError: If fetcher_type is unknown.
            ImportError: If scrapling is not available.
        """
        fetcher_cls = FetcherSelector.for_source("", fetcher_type)

        if fetcher_type == "Fetcher":
            return fetcher_cls.get(url, **kwargs)  # type: ignore[no-untyped-call]
        else:
            # StealthyFetcher and DynamicFetcher use .fetch()
            return fetcher_cls.fetch(url, **kwargs)  # type: ignore[no-untyped-call]

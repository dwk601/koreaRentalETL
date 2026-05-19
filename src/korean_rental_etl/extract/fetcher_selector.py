"""Fetcher selector - factory for creating Scrapling fetchers per source config."""

from __future__ import annotations


class FetcherSelector:
    """Factory that returns appropriately configured Scrapling fetchers."""

    def __init__(self, user_agent: str | None = None) -> None:
        self._user_agent = user_agent or "korean-rental-etl/0.1.0"

    @staticmethod
    def for_source(source_name: str, fetcher_type: str = "StealthyFetcher") -> object:
        """Return a Scrapling fetcher instance configured for the given source.

        Args:
            source_name: Name of the source (for logging/context).
            fetcher_type: Either 'StealthyFetcher' or 'DynamicFetcher'.

        Returns:
            Configured fetcher instance.

        Raises:
            ValueError: If fetcher_type is unknown.
            ImportError: If scrapling or its dependencies are not available.
        """
        if fetcher_type not in ("StealthyFetcher", "DynamicFetcher"):
            raise ValueError(f"Unknown fetcher type: {fetcher_type}")

        try:
            from scrapling import DynamicFetcher, StealthyFetcher
        except (ImportError, ModuleNotFoundError) as e:
            raise ImportError(
                f"scrapling dependencies missing: {e}. "
                "Install with: uv sync (may require system deps like curl_cffi)"
            ) from e

        if fetcher_type == "StealthyFetcher":
            return StealthyFetcher(  # type: ignore[no-untyped-call]
                auto_match=False,
                headless=True,
            )
        else:
            return DynamicFetcher(  # type: ignore[no-untyped-call]
                auto_match=False,
                headless=True,
            )

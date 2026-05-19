"""Fetcher selector - factory for creating Scrapling fetchers per source config."""

from __future__ import annotations


class FetcherSelector:
    """Factory that returns appropriately configured Scrapling fetchers."""

    def __init__(self, user_agent: str | None = None) -> None:
        self._user_agent = user_agent or "korean-rental-etl/0.1.0"

    @staticmethod
    def for_source(source_name: str, fetcher_type: str = "Fetcher") -> object:
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
            raise ImportError(
                f"scrapling not available: {e}. Install with: uv sync"
            ) from e

        if fetcher_type == "Fetcher":
            return Fetcher  # type: ignore[return-value]
        elif fetcher_type == "StealthyFetcher":
            return StealthyFetcher  # type: ignore[return-value]
        else:
            return DynamicFetcher  # type: ignore[return-value]

"""Tests for FetcherSelector."""

import pytest

from korean_rental_etl.extract.fetcher_selector import FetcherSelector


class TestFetcherSelector:
    def test_unknown_fetcher_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown fetcher type"):
            FetcherSelector.for_source("test", "UnknownFetcher")

    def test_stealthy_fetcher_type(self) -> None:
        try:
            fetcher = FetcherSelector.for_source("test", "StealthyFetcher")
            assert fetcher is not None
        except ImportError:
            pytest.skip("scrapling dependencies not available (curl_cffi)")

    def test_dynamic_fetcher_type(self) -> None:
        try:
            fetcher = FetcherSelector.for_source("test", "DynamicFetcher")
            assert fetcher is not None
        except ImportError:
            pytest.skip("scrapling dependencies not available (curl_cffi)")

    def test_import_error_message(self) -> None:
        """Verify ImportError has helpful message when deps are missing."""
        try:
            FetcherSelector.for_source("test", "StealthyFetcher")
        except ImportError as e:
            assert "scrapling dependencies missing" in str(e)
            assert "uv sync" in str(e)

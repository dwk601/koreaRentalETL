"""Tests for ScraperFactory."""

from __future__ import annotations

import pytest

from korean_rental_etl.extract.scraper_factory import ScraperFactory
from korean_rental_etl.extract.scrapers.gtksa import GtksaScraper
from korean_rental_etl.extract.scrapers.ktown_koreadaily import KtownKoreadailyScraper
from korean_rental_etl.extract.scrapers.missyusa import MissyusaScraper
from korean_rental_etl.extract.scrapers.radiokorea import RadiokoreaScraper
from korean_rental_etl.extract.scrapers.svkoreans import SvkoreansScraper
from korean_rental_etl.extract.source_config import SourceConfig


class TestScraperFactory:
    def test_create_svkoreans(self) -> None:
        config = SourceConfig(name="svkoreans", url="https://svkoreans.com")
        scraper = ScraperFactory.create(config, source_id=1)
        assert isinstance(scraper, SvkoreansScraper)
        assert scraper.source_id == 1

    def test_create_gtksa(self) -> None:
        config = SourceConfig(name="gtksa", url="https://gtksa.net")
        scraper = ScraperFactory.create(config, source_id=2)
        assert isinstance(scraper, GtksaScraper)
        assert scraper.source_id == 2

    def test_create_missyusa(self) -> None:
        config = SourceConfig(name="missyusa", url="https://missyusa.com")
        scraper = ScraperFactory.create(config, source_id=3)
        assert isinstance(scraper, MissyusaScraper)
        assert scraper.source_id == 3

    def test_create_ktown_koreadaily(self) -> None:
        config = SourceConfig(name="ktown_koreadaily", url="https://ktown.koreadaily.com")
        scraper = ScraperFactory.create(config, source_id=4)
        assert isinstance(scraper, KtownKoreadailyScraper)
        assert scraper.source_id == 4

    def test_create_radiokorea(self) -> None:
        config = SourceConfig(name="radiokorea", url="https://m.radiokorea.com")
        scraper = ScraperFactory.create(config, source_id=5)
        assert isinstance(scraper, RadiokoreaScraper)
        assert scraper.source_id == 5

    def test_create_unknown_source(self) -> None:
        config = SourceConfig(name="unknown", url="https://example.com")
        with pytest.raises(ValueError, match="Unknown source"):
            ScraperFactory.create(config, source_id=99)

    def test_create_with_custom_delay(self) -> None:
        config = SourceConfig(
            name="svkoreans", url="https://svkoreans.com", download_delay_sec=5.0
        )
        scraper = ScraperFactory.create(config, source_id=1)
        assert scraper._download_delay_sec == 5.0

    def test_available_sources(self) -> None:
        sources = ScraperFactory.available_sources()
        assert "svkoreans" in sources
        assert "gtksa" in sources
        assert "missyusa" in sources
        assert "ktown_koreadaily" in sources
        assert "radiokorea" in sources
        assert len(sources) == 5

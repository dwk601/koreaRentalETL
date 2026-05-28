"""Factory for creating scraper instances from source configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from korean_rental_etl.extract.scrapers.gtksa import GtksaScraper
from korean_rental_etl.extract.scrapers.illinoisksa import IllinoisksaScraper
from korean_rental_etl.extract.scrapers.ktown_koreadaily import KtownKoreadailyScraper
from korean_rental_etl.extract.scrapers.missyusa import MissyusaScraper
from korean_rental_etl.extract.scrapers.radiokorea import RadiokoreaScraper
from korean_rental_etl.extract.scrapers.svkoreans import SvkoreansScraper

if TYPE_CHECKING:
    from korean_rental_etl.extract.base_scraper import BaseScraper
    from korean_rental_etl.extract.source_config import SourceConfig


class ScraperFactory:
    """Factory for creating scraper instances."""

    _scrapers = {
        "svkoreans": SvkoreansScraper,
        "gtksa": GtksaScraper,
        "missyusa": MissyusaScraper,
        "ktown_koreadaily": KtownKoreadailyScraper,
        "radiokorea": RadiokoreaScraper,
        "illinoisksa": IllinoisksaScraper,
    }

    @classmethod
    def create(cls, source_config: SourceConfig, source_id: int) -> BaseScraper:
        """Create a scraper instance for the given source.

        Args:
            source_config: Source configuration.
            source_id: Database ID for the source.

        Returns:
            Scraper instance.

        Raises:
            ValueError: If source name is not recognized.
        """
        scraper_class = cls._scrapers.get(source_config.name)
        if not scraper_class:
            raise ValueError(
                f"Unknown source: {source_config.name}. "
                f"Available: {', '.join(cls._scrapers.keys())}"
            )

        return scraper_class(
            source_id=source_id,
            download_delay_sec=source_config.download_delay_sec,
        )  # type: ignore[return-value]

    @classmethod
    def available_sources(cls) -> list[str]:
        """Return list of available source names."""
        return list(cls._scrapers.keys())

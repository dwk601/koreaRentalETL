"""Source configuration models and loader."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class SourceConfig(BaseModel):
    """Configuration for a single scraping source."""

    name: str
    url: str
    path: str | None = None
    fetcher: Literal["StealthyFetcher", "DynamicFetcher"] = "StealthyFetcher"
    schedule: str | None = None
    download_delay_sec: float = Field(default=2.0, ge=0)
    concurrent_requests: int = Field(default=1, ge=1)
    robots_txt_obey: bool = True
    status: Literal["active", "disabled"] = "active"
    description: str = ""

    @property
    def full_url(self) -> str:
        """Return the full URL combining base url and path."""
        if self.path:
            return f"{self.url.rstrip('/')}/{self.path.lstrip('/')}"
        return self.url

    @property
    def is_active(self) -> bool:
        """Return True if source is active."""
        return self.status == "active"


class SourcesConfig(BaseModel):
    """Top-level sources configuration."""

    sources: list[SourceConfig]


def load_sources(config_path: Path | str | None = None) -> SourcesConfig:
    """Load sources from YAML config file.

    Args:
        config_path: Path to sources.yml. Defaults to config/sources.yml relative to project root.

    Returns:
        Parsed SourcesConfig.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValidationError: If config is invalid.
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "sources.yml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Sources config not found: {config_path}")

    with open(config_path) as f:
        data = yaml.safe_load(f)

    return SourcesConfig.model_validate(data)


def active_sources(config: SourcesConfig) -> list[SourceConfig]:
    """Return only active sources from config."""
    return [s for s in config.sources if s.is_active]


def get_source(config: SourcesConfig, name: str) -> SourceConfig:
    """Get a source by name.

    Raises:
        KeyError: If source not found.
    """
    for s in config.sources:
        if s.name == name:
            return s
    raise KeyError(f"Source not found: {name}")

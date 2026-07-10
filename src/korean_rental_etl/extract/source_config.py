"""Source configuration models and loader."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class SourceConfig(BaseModel):
    """Configuration for a single scraping source."""

    name: str
    url: str
    path: str | None = None
    fetcher: Literal["Fetcher", "StealthyFetcher", "DynamicFetcher"] = "Fetcher"
    schedule: str | None = None
    download_delay_sec: float = Field(default=2.0, ge=0)
    concurrent_requests: int = Field(default=1, ge=1)
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


def _resolve_default_config_path() -> Path:
    """Find sources.yml across dev-mode, installed-image, and env-var paths.

    Resolution order:
    1. KOREAN_RENTAL_ETL_CONFIG_PATH env var (explicit override).
    2. Repo-relative path (dev mode, when running from a checked-out tree).
    3. /opt/airflow/project/config/sources.yml (baked-in production image).
    4. Falls back to the dev-mode path so the FileNotFoundError below carries
       a meaningful message.
    """
    env_path = os.environ.get("KOREAN_RENTAL_ETL_CONFIG_PATH")
    if env_path:
        return Path(env_path)

    candidates = [
        Path(__file__).parent.parent.parent.parent / "config" / "sources.yml",
        Path("/opt/airflow/project/config/sources.yml"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_sources(config_path: Path | str | None = None) -> SourcesConfig:
    """Load sources from YAML config file.

    Args:
        config_path: Path to sources.yml. Defaults to the first match of
            KOREAN_RENTAL_ETL_CONFIG_PATH env var, the repo-relative path,
            or the baked-in production image path.

    Returns:
        Parsed SourcesConfig.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValidationError: If config is invalid.
    """
    config_path = _resolve_default_config_path() if config_path is None else Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Sources config not found: {config_path}")

    with open(config_path) as f:
        data = yaml.safe_load(f)

    return SourcesConfig.model_validate(data)


def active_sources(config: SourcesConfig) -> list[SourceConfig]:
    """Return only active sources from config."""
    return [s for s in config.sources if s.is_active]


def registry_errors(
    configured_active: set[str],
    scraper_names: set[str],
    parser_names: set[str],
    database_active: set[str],
) -> list[str]:
    """Return concise errors when active source registries disagree."""
    errors: list[str] = []
    checks = (
        ("missing scraper", configured_active - scraper_names),
        ("missing parser", configured_active - parser_names),
        ("missing from database", configured_active - database_active),
        ("active only in database", database_active - configured_active),
    )
    for label, names in checks:
        if names:
            errors.append(f"{label}: {', '.join(sorted(names))}")
    return errors


def get_source(config: SourcesConfig, name: str) -> SourceConfig:
    """Get a source by name.

    Raises:
        KeyError: If source not found.
    """
    for s in config.sources:
        if s.name == name:
            return s
    raise KeyError(f"Source not found: {name}")

"""Tests for source config loader and models."""

from pathlib import Path

import pytest

from korean_rental_etl.extract.source_config import (
    SourceConfig,
    SourcesConfig,
    active_sources,
    get_source,
    load_sources,
)

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


class TestSourceConfig:
    def test_full_url_with_path(self) -> None:
        cfg = SourceConfig(name="test", url="https://example.com", path="page/1")
        assert cfg.full_url == "https://example.com/page/1"

    def test_full_url_without_path(self) -> None:
        cfg = SourceConfig(name="test", url="https://example.com")
        assert cfg.full_url == "https://example.com"

    def test_full_url_trailing_slash(self) -> None:
        cfg = SourceConfig(name="test", url="https://example.com/", path="page")
        assert cfg.full_url == "https://example.com/page"

    def test_is_active(self) -> None:
        cfg = SourceConfig(name="test", url="https://example.com", status="active")
        assert cfg.is_active is True

    def test_is_disabled(self) -> None:
        cfg = SourceConfig(name="test", url="https://example.com", status="disabled")
        assert cfg.is_active is False

    def test_default_values(self) -> None:
        cfg = SourceConfig(name="test", url="https://example.com")
        assert cfg.fetcher == "StealthyFetcher"
        assert cfg.download_delay_sec == 2.0
        assert cfg.concurrent_requests == 1
        assert cfg.robots_txt_obey is True
        assert cfg.status == "active"


class TestSourcesConfig:
    def test_load_sources_default_path(self) -> None:
        config = load_sources()
        assert isinstance(config, SourcesConfig)
        assert len(config.sources) == 6

    def test_load_sources_custom_path(self, tmp_path: Path) -> None:
        yaml_content = """
sources:
  - name: test_source
    url: "https://example.com"
    status: active
"""
        config_file = tmp_path / "sources.yml"
        config_file.write_text(yaml_content)
        config = load_sources(config_file)
        assert len(config.sources) == 1
        assert config.sources[0].name == "test_source"

    def test_load_sources_missing_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_sources(Path("/nonexistent/path/sources.yml"))

    def test_load_sources_invalid_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "sources.yml"
        config_file.write_text("sources:\n  - name: incomplete\n")
        with pytest.raises((ValueError, KeyError)):
            load_sources(config_file)


class TestActiveSources:
    def test_active_sources_filters_disabled(self) -> None:
        config = SourcesConfig(
            sources=[
                SourceConfig(name="active1", url="https://a.com", status="active"),
                SourceConfig(name="disabled1", url="https://b.com", status="disabled"),
                SourceConfig(name="active2", url="https://c.com", status="active"),
            ]
        )
        result = active_sources(config)
        assert len(result) == 2
        assert all(s.is_active for s in result)
        assert [s.name for s in result] == ["active1", "active2"]


class TestGetSource:
    def test_get_existing_source(self) -> None:
        config = SourcesConfig(
            sources=[
                SourceConfig(name="alpha", url="https://a.com"),
                SourceConfig(name="beta", url="https://b.com"),
            ]
        )
        result = get_source(config, "beta")
        assert result.name == "beta"

    def test_get_missing_source_raises(self) -> None:
        config = SourcesConfig(sources=[SourceConfig(name="alpha", url="https://a.com")])
        with pytest.raises(KeyError, match="Source not found: missing"):
            get_source(config, "missing")


class TestYamlRoundTrip:
    def test_round_trip(self, tmp_path: Path) -> None:
        yaml_content = """
sources:
  - name: svkoreans
    url: "https://svkoreans.com"
    path: "rent_housing"
    fetcher: StealthyFetcher
    schedule: "0 */6 * * *"
    download_delay_sec: 2.0
    concurrent_requests: 1
    robots_txt_obey: true
    status: active
    description: "SV Korean community"
"""
        config_file = tmp_path / "sources.yml"
        config_file.write_text(yaml_content)
        config = load_sources(config_file)

        assert config.sources[0].name == "svkoreans"
        assert config.sources[0].fetcher == "StealthyFetcher"
        assert config.sources[0].schedule == "0 */6 * * *"
        assert config.sources[0].description == "SV Korean community"

"""Tests for BaseScraper parse_html and _fixture_path helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from korean_rental_etl.extract.scrapers.gtksa import GtksaScraper


class TestParseHtml:
    @pytest.fixture
    def scraper(self) -> GtksaScraper:
        return GtksaScraper(source_id=2)

    def test_parse_html_returns_selector(self, scraper: GtksaScraper) -> None:
        html = "<a href='/x'>hi</a>"
        selector = scraper.parse_html(html)
        assert selector is not None
        # Test native scrapling API
        href = selector.css("a::attr(href)").get()
        assert href == "/x"

    def test_parse_html_with_complex_structure(self, scraper: GtksaScraper) -> None:
        html = """
        <div class="listings">
            <a href="/item/1">Item 1</a>
            <a href="/item/2">Item 2</a>
        </div>
        """
        selector = scraper.parse_html(html)
        items = selector.css("a::attr(href)").getall()
        assert len(items) == 2
        assert "/item/1" in items
        assert "/item/2" in items

    def test_parse_html_text_extraction(self, scraper: GtksaScraper) -> None:
        html = "<div><span>Hello</span> <span>World</span></div>"
        selector = scraper.parse_html(html)
        text = selector.css("span::text").getall()
        assert "Hello" in text
        assert "World" in text


class TestFixturePath:
    @pytest.fixture
    def scraper(self) -> GtksaScraper:
        return GtksaScraper(source_id=2)

    def test_fixture_path_resolves_correctly(self, scraper: GtksaScraper) -> None:
        path = scraper._fixture_path("list_page_1.html")
        assert path.name == "list_page_1.html"
        assert "gtksa" in str(path)
        assert "fixtures" in str(path)

    def test_fixture_path_exists_for_gtksa(self, scraper: GtksaScraper) -> None:
        path = scraper._fixture_path("list_page_1.html")
        assert path.exists(), f"Fixture not found at {path}"

    def test_fixture_path_for_different_sources(self) -> None:
        from korean_rental_etl.extract.scrapers.svkoreans import SvkoreansScraper

        scraper = SvkoreansScraper(source_id=1)
        path = scraper._fixture_path("list_page_1.html")
        assert "svkoreans" in str(path)
        assert path.exists()

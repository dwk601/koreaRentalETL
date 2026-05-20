"""Tests for BaseScraper parse_html and _fixture_path helpers."""

from __future__ import annotations

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


class TestBuildListing:
    """Tests for BaseScraper._build_listing - location signal extraction."""

    @pytest.fixture
    def scraper(self) -> GtksaScraper:
        return GtksaScraper(source_id=2)

    def test_build_listing_extracts_bracket_location(self, scraper: GtksaScraper) -> None:
        listing = scraper._build_listing(
            url="https://example.com/1",
            source_listing_id="1",
            title="[LA] 다운타운 1베드룸 월세",
        )
        assert listing == {
            "url": "https://example.com/1",
            "source_listing_id": "1",
            "title": "[LA] 다운타운 1베드룸 월세",
            "location": "LA",
        }

    def test_build_listing_korean_bracket(self, scraper: GtksaScraper) -> None:
        listing = scraper._build_listing(
            url="https://example.com/2",
            source_listing_id="2",
            title="[애틀랜타] 룸메이트 구합니다",
        )
        assert listing["location"] == "애틀랜타"

    def test_build_listing_no_bracket(self, scraper: GtksaScraper) -> None:
        listing = scraper._build_listing(
            url="https://example.com/3",
            source_listing_id="3",
            title="아파트 렌트합니다",
        )
        assert listing["location"] == ""

    def test_build_listing_empty_title(self, scraper: GtksaScraper) -> None:
        listing = scraper._build_listing(
            url="https://example.com/4",
            source_listing_id="4",
            title="",
        )
        assert listing["location"] == ""

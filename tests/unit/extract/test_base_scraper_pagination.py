"""Tests for BaseScraper pagination helpers."""

from korean_rental_etl.extract.base_scraper import BaseScraper


class MockScraper(BaseScraper):
    """Mock scraper for testing."""

    source_name = "test"
    _list_url = "https://example.com/list"

    def crawl_list_pages(self):
        return iter([])

    def fetch_detail(self, url: str):
        return {"html": "", "status": 200, "url": url}


class TestBuildPageUrl:
    """Test _build_page_url helper."""

    def test_build_page_url_no_existing_query(self) -> None:
        scraper = MockScraper(source_id=1)
        url = scraper._build_page_url("https://example.com/list", 2)
        assert url == "https://example.com/list?page=2"

    def test_build_page_url_with_existing_query(self) -> None:
        scraper = MockScraper(source_id=1)
        url = scraper._build_page_url("https://example.com/board?bo_table=rent", 3)
        assert "page=3" in url
        assert "bo_table=rent" in url

    def test_build_page_url_replaces_existing_page(self) -> None:
        scraper = MockScraper(source_id=1)
        url = scraper._build_page_url("https://example.com/?page=1&foo=bar", 5)
        assert "page=5" in url
        assert "foo=bar" in url
        assert "page=1" not in url

    def test_build_page_url_preserves_fragment(self) -> None:
        scraper = MockScraper(source_id=1)
        url = scraper._build_page_url("https://example.com/#top", 2)
        assert url.endswith("#top")
        assert "page=2" in url


class TestPaginatedListUrls:
    """Test _paginated_list_urls helper."""

    def test_paginated_list_urls_iterates_max(self) -> None:
        scraper = MockScraper(source_id=1)
        scraper.max_pages = 3
        urls = list(scraper._paginated_list_urls())
        assert len(urls) == 3
        assert "page=1" in urls[0]
        assert "page=2" in urls[1]
        assert "page=3" in urls[2]

    def test_paginated_list_urls_custom_max(self) -> None:
        scraper = MockScraper(source_id=1)
        scraper.max_pages = 20
        urls = list(scraper._paginated_list_urls(max_pages=5))
        assert len(urls) == 5

    def test_paginated_list_urls_subclass_override(self) -> None:
        class CustomScraper(MockScraper):
            max_pages = 10

        scraper = CustomScraper(source_id=1)
        urls = list(scraper._paginated_list_urls())
        assert len(urls) == 10

    def test_paginated_list_urls_no_list_url_raises(self) -> None:
        class NoListUrlScraper(BaseScraper):
            source_name = "test"

            def crawl_list_pages(self):
                return iter([])

            def fetch_detail(self, url: str):
                return {"html": "", "status": 200, "url": url}

        scraper = NoListUrlScraper(source_id=1)
        try:
            list(scraper._paginated_list_urls())
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "_list_url not set" in str(e)

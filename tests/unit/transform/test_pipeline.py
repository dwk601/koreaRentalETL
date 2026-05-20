"""Unit tests for transform pipeline."""

from unittest.mock import MagicMock, patch

from korean_rental_etl.transform.pipeline import transform_row


class TestTransformRow:
    """Test transform_row function."""

    def test_valid_row_with_all_fields(self):
        """Transform a valid row with all fields."""
        raw_page = {
            "html_content": "<html><body>test</body></html>",
            "url": "https://svkoreans.com/rent_housing/12345",
            "content_hash": "a" * 64,
        }

        mock_parser = MagicMock()
        mock_parser.parse_detail.return_value = {
            "title_ko": "[LA] 테스트 아파트",
            "body_ko": "테스트 본문",
            "raw_price": "$1,500",
            "raw_location": "LA",
            "raw_posted_at": "2024-05-01",
            "contact_block": "213-555-1234",
            "source_listing_id": "12345",
            "url": "https://svkoreans.com/rent_housing/12345",
            "content_hash": "a" * 64,
        }

        with patch("korean_rental_etl.transform.pipeline._get_parser") as mock_get_parser:
            mock_get_parser.return_value = mock_parser

            with patch("korean_rental_etl.transform.pipeline.geocode") as mock_geocode:
                mock_geocode.return_value = {"lat": 34.05, "lon": -118.25}

                result = transform_row("svkoreans", 1, raw_page)

                assert result is not None
                assert result["title_ko"] == "[LA] 테스트 아파트"
                assert result["rent_monthly_usd"] == 1500.00
                assert result["city"] in ("La", "Los Angeles")  # Normalizer may match "la"
                assert result["category"] == "apartment"
                assert result["lat"] == 34.05
                assert result["lon"] == -118.25

    def test_skip_row_with_no_title_and_no_price(self):
        """Skip row if both title_ko and raw_price are empty."""
        raw_page = {
            "html_content": "<html><body>test</body></html>",
            "url": "https://svkoreans.com/rent_housing/99999",
            "content_hash": "b" * 64,
        }

        mock_parser = MagicMock()
        mock_parser.parse_detail.return_value = {
            "title_ko": "",
            "body_ko": "Some body",
            "raw_price": "",
            "raw_location": "LA",
            "raw_posted_at": "2024-05-01",
            "contact_block": "",
            "source_listing_id": "99999",
            "url": "https://svkoreans.com/rent_housing/99999",
            "content_hash": "b" * 64,
        }

        with patch("korean_rental_etl.transform.pipeline._get_parser") as mock_get_parser:
            mock_get_parser.return_value = mock_parser

            result = transform_row("svkoreans", 1, raw_page)
            assert result is None

    def test_geocode_failure_is_non_fatal(self):
        """Geocoding failure should not prevent row insertion."""
        raw_page = {
            "html_content": "<html><body>test</body></html>",
            "url": "https://svkoreans.com/rent_housing/12346",
            "content_hash": "c" * 64,
        }

        mock_parser = MagicMock()
        mock_parser.parse_detail.return_value = {
            "title_ko": "[OC] 테스트 콘도",
            "body_ko": "테스트 본문",
            "raw_price": "$2,000",
            "raw_location": "OC",
            "raw_posted_at": "2024-05-02",
            "contact_block": "949-555-5678",
            "source_listing_id": "12346",
            "url": "https://svkoreans.com/rent_housing/12346",
            "content_hash": "c" * 64,
        }

        with patch("korean_rental_etl.transform.pipeline._get_parser") as mock_get_parser:
            mock_get_parser.return_value = mock_parser

            with patch("korean_rental_etl.transform.pipeline.geocode") as mock_geocode:
                mock_geocode.side_effect = Exception("Geocoding service down")

                result = transform_row("svkoreans", 1, raw_page)

                assert result is not None
                assert result["lat"] is None
                assert result["lon"] is None
                assert result["title_ko"] == "[OC] 테스트 콘도"

    def test_empty_address_skips_geocoding(self):
        """Skip geocoding if address_raw is empty."""
        raw_page = {
            "html_content": "<html><body>test</body></html>",
            "url": "https://svkoreans.com/rent_housing/12347",
            "content_hash": "d" * 64,
        }

        mock_parser = MagicMock()
        mock_parser.parse_detail.return_value = {
            "title_ko": "[SF] 테스트 스튜디오",
            "body_ko": "테스트 본문",
            "raw_price": "$2,500",
            "raw_location": "",  # Empty location
            "raw_posted_at": "2024-05-03",
            "contact_block": "415-555-9012",
            "source_listing_id": "12347",
            "url": "https://svkoreans.com/rent_housing/12347",
            "content_hash": "d" * 64,
        }

        with patch("korean_rental_etl.transform.pipeline._get_parser") as mock_get_parser:
            mock_get_parser.return_value = mock_parser

            with patch("korean_rental_etl.transform.pipeline.geocode") as mock_geocode:
                result = transform_row("svkoreans", 1, raw_page)

                # geocode should not be called
                mock_geocode.assert_not_called()
                assert result is not None
                assert result["lat"] is None
                assert result["lon"] is None

    def test_parser_exception_returns_none(self):
        """Parser exception should return None."""
        raw_page = {
            "html_content": "<html><body>test</body></html>",
            "url": "https://svkoreans.com/rent_housing/99998",
            "content_hash": "e" * 64,
        }

        mock_parser = MagicMock()
        mock_parser.parse_detail.side_effect = Exception("Parse error")

        with patch("korean_rental_etl.transform.pipeline._get_parser") as mock_get_parser:
            mock_get_parser.return_value = mock_parser

            result = transform_row("svkoreans", 1, raw_page)
            assert result is None

"""Unit tests for geocoder."""

from korean_rental_etl.transform.geocoder import geocode


class TestGeocoder:
    """Test Nominatim geocoder."""

    def test_empty_address_returns_none(self):
        """Empty address should return None."""
        result = geocode("")
        assert result == {"lat": None, "lon": None}

    def test_cache_hit(self, mocker):
        """Should return cached result on cache hit."""
        mock_redis = mocker.MagicMock()
        mock_redis.get.return_value = "40.7128,-74.0060"
        mocker.patch(
            "korean_rental_etl.transform.geocoder.get_redis_client", return_value=mock_redis
        )

        result = geocode("New York", "NY", "US")
        assert result["lat"] == 40.7128
        assert result["lon"] == -74.0060

    def test_cache_miss_success(self, mocker):
        """Should call Nominatim on cache miss and cache result."""
        mock_redis = mocker.MagicMock()
        mock_redis.get.return_value = None
        mocker.patch(
            "korean_rental_etl.transform.geocoder.get_redis_client", return_value=mock_redis
        )

        mock_response = mocker.MagicMock()
        mock_response.json.return_value = [{"lat": "40.7128", "lon": "-74.0060"}]
        mocker.patch("korean_rental_etl.transform.geocoder.httpx.get", return_value=mock_response)

        result = geocode("New York", "NY", "US")
        assert result["lat"] == 40.7128
        assert result["lon"] == -74.0060
        mock_redis.setex.assert_called_once()

    def test_nominatim_failure(self, mocker):
        """Should return None on Nominatim failure."""
        mock_redis = mocker.MagicMock()
        mock_redis.get.return_value = None
        mocker.patch(
            "korean_rental_etl.transform.geocoder.get_redis_client", return_value=mock_redis
        )

        mocker.patch(
            "korean_rental_etl.transform.geocoder.httpx.get", side_effect=Exception("Network error")
        )

        result = geocode("Invalid Address XYZ", "XX", "ZZ")
        assert result == {"lat": None, "lon": None}

    def test_no_results(self, mocker):
        """Should return None when Nominatim returns no results."""
        mock_redis = mocker.MagicMock()
        mock_redis.get.return_value = None
        mocker.patch(
            "korean_rental_etl.transform.geocoder.get_redis_client", return_value=mock_redis
        )

        mock_response = mocker.MagicMock()
        mock_response.json.return_value = []
        mocker.patch("korean_rental_etl.transform.geocoder.httpx.get", return_value=mock_response)

        result = geocode("Nonexistent Place", "XX", "ZZ")
        assert result == {"lat": None, "lon": None}

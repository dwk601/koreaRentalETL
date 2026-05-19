"""Integration tests for geocoder (placeholder)."""

import pytest


@pytest.mark.integration
class TestGeocoderIntegration:
    """Integration tests for geocoder against test Redis."""

    def test_geocode_with_redis_cache(self):
        """Test geocoding with Redis cache (requires docker-compose.test.yml)."""
        pytest.skip("Integration test requires docker-compose.test.yml")

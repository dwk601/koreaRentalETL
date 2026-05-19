"""Integration tests for extractors (placeholder)."""

import pytest


@pytest.mark.integration
class TestExtractorIntegration:
    """Integration tests for per-source extractors."""

    def test_extract_all_from_fixtures(self):
        """Test extract --all against fixtures (requires docker-compose.test.yml)."""
        pytest.skip("Integration test requires docker-compose.test.yml")

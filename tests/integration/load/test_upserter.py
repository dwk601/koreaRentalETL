"""Integration tests for upserter (placeholder)."""

import pytest


@pytest.mark.integration
class TestUpserterIntegration:
    """Integration tests for batched upserter."""

    def test_upsert_batch_roundtrip(self):
        """Test staging→public roundtrip (requires docker-compose.test.yml)."""
        pytest.skip("Integration test requires docker-compose.test.yml")

"""Unit tests for redis_layer module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from korean_rental_etl.transform.dedup.redis_layer import (
    _key,
    clear,
    count,
    mark,
    mark_batch,
    seen,
)


class TestKey:
    def test_key_format(self) -> None:
        assert _key("svkoreans") == "seen_urls:svkoreans"


class TestSeen:
    @patch("korean_rental_etl.transform.dedup.redis_layer.get_redis_client")
    def test_returns_true_when_member(self, mock_get_redis: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.sismember.return_value = True
        mock_get_redis.return_value = mock_client

        assert seen("svkoreans", "https://example.com/1") is True
        mock_client.sismember.assert_called_once_with("seen_urls:svkoreans", "https://example.com/1")

    @patch("korean_rental_etl.transform.dedup.redis_layer.get_redis_client")
    def test_returns_false_when_not_member(self, mock_get_redis: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.sismember.return_value = False
        mock_get_redis.return_value = mock_client

        assert seen("svkoreans", "https://example.com/new") is False


class TestMark:
    @patch("korean_rental_etl.transform.dedup.redis_layer.get_redis_client")
    def test_adds_to_set(self, mock_get_redis: MagicMock) -> None:
        mock_client = MagicMock()
        mock_get_redis.return_value = mock_client

        mark("svkoreans", "https://example.com/1")
        mock_client.sadd.assert_called_once_with("seen_urls:svkoreans", "https://example.com/1")
        mock_client.expire.assert_called_once()


class TestMarkBatch:
    @patch("korean_rental_etl.transform.dedup.redis_layer.get_redis_client")
    def test_batch_add(self, mock_get_redis: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.sadd.return_value = 3
        mock_get_redis.return_value = mock_client

        urls = ["https://a.com", "https://b.com", "https://c.com"]
        added = mark_batch("svkoreans", urls)
        assert added == 3
        mock_client.sadd.assert_called_once_with("seen_urls:svkoreans", *urls)

    @patch("korean_rental_etl.transform.dedup.redis_layer.get_redis_client")
    def test_empty_batch(self, mock_get_redis: MagicMock) -> None:
        added = mark_batch("svkoreans", [])
        assert added == 0


class TestCount:
    @patch("korean_rental_etl.transform.dedup.redis_layer.get_redis_client")
    def test_returns_count(self, mock_get_redis: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.scard.return_value = 42
        mock_get_redis.return_value = mock_client

        assert count("svkoreans") == 42


class TestClear:
    @patch("korean_rental_etl.transform.dedup.redis_layer.get_redis_client")
    def test_deletes_key(self, mock_get_redis: MagicMock) -> None:
        mock_client = MagicMock()
        mock_get_redis.return_value = mock_client

        clear("svkoreans")
        mock_client.delete.assert_called_once_with("seen_urls:svkoreans")

"""Unit tests for connection module."""

import pytest
from korean_rental_etl.db.connection import get_db_config


def test_get_db_config_raises_without_password(monkeypatch):
    """get_db_config raises RuntimeError when POSTGRES_PASSWORD is not set or is empty."""
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="POSTGRES_PASSWORD is not set"):
        get_db_config()


def test_get_db_config_raises_with_empty_password(monkeypatch):
    """get_db_config raises RuntimeError when POSTGRES_PASSWORD is set but empty."""
    monkeypatch.setenv("POSTGRES_PASSWORD", "")
    with pytest.raises(RuntimeError, match="POSTGRES_PASSWORD is not set"):
        get_db_config()


def test_get_db_config_succeeds_with_password(monkeypatch):
    """get_db_config returns config dict when password is set."""
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret_pass")
    cfg = get_db_config()
    assert cfg["password"] == "secret_pass"
    assert cfg["host"] == "localhost"
    assert cfg["port"] == 5432
    assert cfg["dbname"] == "korean_rental"
    assert cfg["user"] == "etl_user"

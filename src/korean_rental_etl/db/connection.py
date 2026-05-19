"""Database connection management with psycopg connection pool."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import TYPE_CHECKING

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

if TYPE_CHECKING:
    from collections.abc import Generator

    import psycopg

_pool: ConnectionPool | None = None


def get_db_config() -> dict[str, str | int]:
    """Get database configuration from environment variables."""
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "dbname": os.environ.get("POSTGRES_DB", "korean_rental"),
        "user": os.environ.get("POSTGRES_USER", "etl_user"),
        "password": os.environ.get("POSTGRES_PASSWORD", "change_me_in_production"),
    }


def get_conninfo() -> str:
    """Build psycopg connection string from env vars."""
    cfg = get_db_config()
    return (
        f"host={cfg['host']} port={cfg['port']} "
        f"dbname={cfg['dbname']} user={cfg['user']} password={cfg['password']}"
    )


def init_pool(min_size: int = 2, max_size: int = 10) -> ConnectionPool:
    """Initialize the global connection pool.

    Args:
        min_size: Minimum number of connections in pool.
        max_size: Maximum number of connections in pool.

    Returns:
        Initialized ConnectionPool.
    """
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=get_conninfo(),
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
        )
    return _pool


def close_pool() -> None:
    """Close the global connection pool."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def get_connection() -> Generator[psycopg.Connection, None, None]:
    """Get a connection from the pool.

    Yields:
        A psycopg Connection with dict_row factory.

    Usage:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    """
    pool = init_pool()
    with pool.connection() as conn:
        yield conn


@contextmanager
def get_cursor() -> Generator[psycopg.Cursor, None, None]:
    """Get a cursor from a pooled connection.

    Yields:
        A psycopg Cursor with dict_row factory.

    Usage:
        with get_cursor() as cur:
            cur.execute("SELECT 1")
            rows = cur.fetchall()
    """
    with get_connection() as conn, conn.cursor() as cur:
        yield cur


def test_connection() -> bool:
    """Test database connectivity.

    Returns:
        True if connection succeeds.
    """
    try:
        with get_cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()
            return result is not None
    except Exception:
        return False

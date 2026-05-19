"""Smoke tests to verify project setup."""

from korean_rental_etl import __version__


def test_version_string() -> None:
    """Version is a valid semver string."""
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_package_importable() -> None:
    """Package can be imported."""
    import korean_rental_etl

    assert korean_rental_etl is not None


def test_cli_importable() -> None:
    """CLI module can be imported."""
    from korean_rental_etl.cli.cli import main

    assert callable(main)

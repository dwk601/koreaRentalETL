"""Korean Rental ETL - Command Line Interface."""

import click

from korean_rental_etl import __version__


@click.group()
@click.version_option(version=__version__, prog_name="korean-rental-etl")
def main() -> None:
    """Korean Rental ETL - Scrape, transform, and load Korean rental listings."""
    pass


@main.command()
def sources() -> None:
    """List configured sources."""
    click.echo("Sources command placeholder")


@main.command()
@click.option("--source", help="Source name to extract from")
def extract(source: str | None) -> None:
    """Extract listings from sources."""
    click.echo(f"Extract command placeholder (source={source})")


@main.command()
@click.option("--run-id", help="ETL run ID")
def transform(run_id: str | None) -> None:
    """Transform extracted listings."""
    click.echo(f"Transform command placeholder (run_id={run_id})")


@main.command()
@click.option("--run-id", help="ETL run ID")
def load(run_id: str | None) -> None:
    """Load transformed listings into database."""
    click.echo(f"Load command placeholder (run_id={run_id})")


@main.command()
@click.option("--run-id", help="ETL run ID")
def validate(run_id: str | None) -> None:
    """Validate loaded listings."""
    click.echo(f"Validate command placeholder (run_id={run_id})")


@main.command()
def run_all() -> None:
    """Run full ETL pipeline (extract -> transform -> load -> validate)."""
    click.echo("run-all command placeholder")


if __name__ == "__main__":
    main()

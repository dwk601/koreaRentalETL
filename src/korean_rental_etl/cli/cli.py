"""Korean Rental ETL - Command Line Interface."""

import click

from korean_rental_etl import __version__


@click.group()
@click.version_option(version=__version__, prog_name="korean-rental-etl")
def main() -> None:
    """Korean Rental ETL - Scrape, transform, and load Korean rental listings."""
    pass


@main.group()
def sources() -> None:
    """Manage source configurations."""
    pass


@sources.command("list")
def sources_list() -> None:
    """List all configured sources."""
    from korean_rental_etl.extract.source_config import load_sources

    config = load_sources()
    for s in config.sources:
        status = "✓" if s.is_active else "✗"
        click.echo(f"  {status} {s.name:20s} {s.fetcher:20s} {s.full_url}")


@sources.command("show")
@click.argument("name")
def sources_show(name: str) -> None:
    """Show details for a specific source."""
    from korean_rental_etl.extract.source_config import get_source, load_sources

    config = load_sources()
    try:
        s = get_source(config, name)
    except KeyError as e:
        click.echo(f"Source not found: {name}", err=True)
        raise SystemExit(1) from e

    click.echo(f"Name:        {s.name}")
    click.echo(f"URL:         {s.full_url}")
    click.echo(f"Fetcher:     {s.fetcher}")
    click.echo(f"Schedule:    {s.schedule or 'disabled'}")
    click.echo(f"Delay:       {s.download_delay_sec}s")
    click.echo(f"Status:      {s.status}")
    click.echo(f"Description: {s.description}")


@main.command()
@click.option("--source", help="Source name to extract from")
@click.option("--all", "extract_all", is_flag=True, help="Extract from all active sources")
def extract(source: str | None, extract_all: bool) -> None:
    """Extract listings from sources."""
    if extract_all:
        click.echo("Extracting from all active sources...")
    elif source:
        click.echo(f"Extracting from {source}...")
    else:
        click.echo("Please specify --source or --all")


@main.command()
@click.option("--run-id", help="ETL run ID")
def transform(run_id: str | None) -> None:
    """Transform extracted listings (parse, geocode, classify, dedup)."""
    click.echo("Transforming listings...")


@main.command()
@click.option("--run-id", help="ETL run ID")
def load(run_id: str | None) -> None:
    """Load transformed listings into database."""
    click.echo("Loading listings...")


@main.command()
@click.option("--run-id", help="ETL run ID")
def validate(run_id: str | None) -> None:
    """Validate loaded listings."""
    click.echo("Validating listings...")


@main.command()
def run_all() -> None:
    """Run full ETL pipeline (extract -> transform -> load -> validate)."""
    click.echo("run-all command placeholder")


if __name__ == "__main__":
    main()

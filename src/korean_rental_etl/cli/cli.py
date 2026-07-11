"""Korean Rental ETL - Command Line Interface."""

import time

import click

from korean_rental_etl import __version__


def source_registry_errors() -> list[str]:
    """Compare active YAML sources with scraper, parser, and database registries."""
    from korean_rental_etl.db.connection import get_cursor
    from korean_rental_etl.extract.scraper_factory import ScraperFactory
    from korean_rental_etl.extract.source_config import (
        active_sources,
        load_sources,
        registry_errors,
    )
    from korean_rental_etl.transform.pipeline import _get_parser

    configured = {source.name for source in active_sources(load_sources())}
    with get_cursor() as cur:
        cur.execute("SELECT name FROM public.sources WHERE is_active = TRUE")
        database = {str(row["name"]) for row in cur.fetchall()}
    return registry_errors(
        configured,
        set(ScraperFactory.available_sources()),
        {name for name in configured if _get_parser(name) is not None},
        database,
    )


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


@sources.command("check")
def sources_check() -> None:
    """Verify YAML, code, and database source registries are aligned."""
    errors = source_registry_errors()
    if errors:
        for error in errors:
            click.echo(f"  ✗ {error}", err=True)
        raise SystemExit(1)
    click.echo("✓ Source registries aligned")


@main.command()
@click.option("--source", help="Source name to extract from")
@click.option("--all", "extract_all", is_flag=True, help="Extract from all active sources")
@click.option("--dag-id", help="Workflow ID retained in the audit schema")
@click.option("--run-id", help="Workflow run ID")
def extract(source: str | None, extract_all: bool, dag_id: str | None, run_id: str | None) -> None:
    """Extract listings from sources."""
    from korean_rental_etl.extract.scraper_factory import ScraperFactory
    from korean_rental_etl.extract.source_config import active_sources, get_source, load_sources
    from korean_rental_etl.transform.pipeline import get_source_id_by_name

    config = load_sources()

    if not extract_all and not source:
        click.echo("Error: Please specify --source or --all", err=True)
        raise SystemExit(1)

    if extract_all:
        errors = source_registry_errors()
        if errors:
            click.echo("Source preflight failed:", err=True)
            for error in errors:
                click.echo(f"  ✗ {error}", err=True)
            raise SystemExit(1)

    sources_to_extract = []
    if extract_all:
        sources_to_extract = active_sources(config)
    else:
        try:
            assert source is not None
            sources_to_extract = [get_source(config, source)]
        except KeyError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1) from e

    for src_config in sources_to_extract:
        try:
            click.echo(f"Extracting from {src_config.name}...")
            started = time.monotonic()
            source_id = get_source_id_by_name(src_config.name)
            scraper = ScraperFactory.create(src_config, source_id=source_id)
            extracted, skipped = scraper.extract(dag_id=dag_id, run_id=run_id)
            elapsed = time.monotonic() - started
            click.echo(
                f"  ✓ Extracted {extracted} listings, skipped {skipped}; "
                f"elapsed_seconds={elapsed:.1f}"
            )
        except Exception as e:
            click.echo(f"  ✗ Error: {e}", err=True)
            raise SystemExit(1) from e


@main.command()
@click.option("--source", help="Source name to transform")
@click.option("--all", "transform_all", is_flag=True, help="Transform all active sources")
@click.option("--limit", type=int, default=500, help="Max rows to process per source")
@click.option("--dag-id", help="Workflow ID retained in the audit schema")
@click.option("--run-id", help="Workflow run ID")
def transform(
    source: str | None,
    transform_all: bool,
    limit: int,
    dag_id: str | None,
    run_id: str | None,
) -> None:
    """Transform extracted listings (parse, geocode, classify, dedup)."""
    from korean_rental_etl.transform.pipeline import run

    if not transform_all and not source:
        click.echo("Error: Please specify --source or --all", err=True)
        raise SystemExit(1)

    try:
        if transform_all:
            click.echo("Transforming all sources...")
            rows_parsed, rows_failed = run(
                source_name=None, limit=limit, dag_id=dag_id, run_id=run_id
            )
        else:
            click.echo(f"Transforming {source}...")
            rows_parsed, rows_failed = run(
                source_name=source, limit=limit, dag_id=dag_id, run_id=run_id
            )

        click.echo(f"  ✓ Transformed {rows_parsed} listings, failed {rows_failed}")
    except Exception as e:
        click.echo(f"  ✗ Error: {e}", err=True)
        raise SystemExit(1) from e


@main.command()
@click.option("--source", help="Source name to load")
@click.option("--dag-id", help="Workflow ID retained in the audit schema")
@click.option("--run-id", help="Workflow run ID")
def load(source: str | None, dag_id: str | None, run_id: str | None) -> None:
    """Load transformed listings into database."""
    from korean_rental_etl.load.upserter import load_from_staging
    from korean_rental_etl.transform.pipeline import get_source_id_by_name

    source_id = None
    if source:
        try:
            source_id = get_source_id_by_name(source)
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1) from e

    try:
        click.echo("Loading listings...")
        loaded, failed = load_from_staging(source_id=source_id, dag_id=dag_id, run_id=run_id)
        click.echo(f"  ✓ Loaded {loaded} listings, failed {failed}")
    except Exception as e:
        click.echo(f"  ✗ Error: {e}", err=True)
        raise SystemExit(1) from e


@main.command()
@click.option("--run-id", help="ETL run ID (workflow run ID string or numeric DB ID)")
def validate(run_id: str | None) -> None:
    """Validate loaded listings."""
    if not run_id:
        click.echo(
            "Error: Please specify --run-id (Airflow run ID string or numeric DB ID)", err=True
        )
        raise SystemExit(1)

    from korean_rental_etl.validation.thresholds import (
        ValidationError,
        get_audit_run_id_by_airflow_run_id,
        validate_run,
    )

    try:
        db_run_id = get_audit_run_id_by_airflow_run_id(run_id, task_id="transform")
        click.echo(f"Validating run {run_id} (audit_id={db_run_id})...")
        report = validate_run(db_run_id)
        click.echo("  ✓ Validation passed!")
        for check in report["checks"]:
            status = "✓" if check["passed"] else "✗"
            click.echo(f"    {status} {check['name']}: {check['message']}")
    except ValidationError as e:
        click.echo(f"  ✗ Validation failed: {e}", err=True)
        raise SystemExit(1) from e
    except Exception as e:
        click.echo(f"  ✗ Error: {e}", err=True)
        raise SystemExit(1) from e


@main.command("run-all")
@click.option("--dag-id", help="Workflow ID retained in the audit schema")
@click.option("--run-id", help="Workflow run ID")
@click.pass_context
def run_all(ctx: click.Context, dag_id: str | None, run_id: str | None) -> None:
    """Run full ETL pipeline (extract -> transform -> load -> validate)."""
    from datetime import UTC, datetime

    if not run_id:
        run_id = f"cli_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    if not dag_id:
        dag_id = "cli_run_all"

    try:
        click.echo(">>> Step 1/4: Extracting...")
        ctx.invoke(extract, extract_all=True, source=None, dag_id=dag_id, run_id=run_id)

        click.echo(">>> Step 2/4: Transforming...")
        ctx.invoke(
            transform, transform_all=True, source=None, limit=500, dag_id=dag_id, run_id=run_id
        )

        click.echo(">>> Step 3/4: Loading...")
        ctx.invoke(load, source=None, dag_id=dag_id, run_id=run_id)

        click.echo(">>> Step 4/4: Validating...")
        from korean_rental_etl.validation.thresholds import get_audit_run_id_by_airflow_run_id

        db_run_id = get_audit_run_id_by_airflow_run_id(run_id, task_id="transform")
        ctx.invoke(validate, run_id=str(db_run_id))
        click.echo(">>> ETL Pipeline run-all completed successfully!")
    except Exception as e:
        click.echo(f"  ✗ run-all failed: {e}", err=True)
        raise SystemExit(1) from e


@main.group()
def cleanup() -> None:
    """Cleanup stale listings and old raw pages."""
    pass


@cleanup.command("mark-stale")
@click.option("--days", type=int, default=14, help="Number of days")
def mark_stale(days: int) -> None:
    """Mark listings as inactive if not seen in N days."""
    from korean_rental_etl.load.cleanup import mark_stale_listings_inactive

    try:
        count = mark_stale_listings_inactive(days=days)
        click.echo(f"  ✓ Marked {count} listings as inactive")
    except Exception as e:
        click.echo(f"  ✗ Error: {e}", err=True)
        raise SystemExit(1) from e


@cleanup.command("purge-pages")
@click.option("--days", type=int, default=90, help="Number of days")
def purge_pages(days: int) -> None:
    """Delete raw HTML pages older than N days."""
    from korean_rental_etl.load.cleanup import purge_old_raw_pages

    try:
        count = purge_old_raw_pages(days=days)
        click.echo(f"  ✓ Purged {count} raw pages")
    except Exception as e:
        click.echo(f"  ✗ Error: {e}", err=True)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()

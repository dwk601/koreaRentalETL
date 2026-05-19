# Korean Rental ETL

ETL pipeline for scraping, transforming, and loading Korean rental listings from community boards.

## Sources

- **svkoreans** - svkoreans.com/rent_housing
- **gtksa** - gtksa.net/bbs/board.php?bo_table=rent
- **missyusa** - missyusa.com/town9
- **ktown_koreadaily** - ktown.koreadaily.com/ad_rent/rentlist
- **radiokorea** - m.radiokorea.com/c_realestate
- **hanintown** - hanintown.com (disabled)

## Quick Start

```bash
# Copy environment file
cp .env.example .env

# Start services
docker compose up -d postgres redis

# Install dependencies
make dev

# Run tests
make test

# Run full CI
make ci
```

## Development

```bash
make help          # Show available targets
make lint          # Run linter
make typecheck     # Run type checker
make test          # Run unit tests
make test-integration  # Run integration tests
make format        # Auto-format code
```

## Architecture

- **Extract**: Scrapling-based scrapers with Cloudflare bypass
- **Transform**: Korean normalization, geocoding, deduplication
- **Load**: PostgreSQL with pg_trgm full-text search
- **Orchestration**: Apache Airflow (6-hour schedule)

## License

MIT

# Scrapling Skill

A Claude skill for writing complete, production-ready web scraping scripts using the [Scrapling](https://github.com/D4Vinci/Scrapling) library.

## Install via skills.sh

```bash
npx skills add dwk601/scrapling-skill
```

Or install to specific agents:

```bash
npx skills add dwk601/scrapling-skill -a claude-code -a opencode -a cursor
```

Or install globally:

```bash
npx skills add dwk601/scrapling-skill -g
```

## What this skill does

This skill helps Claude write Python web scraping scripts that are:
- **Correct** — Uses the right Scrapling fetcher for the job (HTTP, browser, or stealth)
- **Complete** — Handles pagination, retries, data export, and edge cases
- **Idiomatic** — Follows Scrapling best practices (selectors, sessions, spiders, adaptive scraping)

## What gets triggered

This skill activates when you ask Claude to:
- Scrape data from any website
- Extract structured data (products, jobs, articles, prices, etc.)
- Crawl multiple pages or follow links
- Bypass anti-bot protection (Cloudflare, CAPTCHA, WAF)
- Automate browser interactions for data extraction
- Build a scraping spider or crawler
- Migrate from BeautifulSoup or Scrapy

## Skill contents

```
scrapling-skill/
├── SKILL.md              # Main instructions for Claude
└── references/
    ├── fetchers.md       # Fetcher classes, sessions, proxies, anti-bot
    ├── parsing.md        # Selection methods (CSS, XPath, find_similar, adaptive)
    └── spiders.md        # Spider framework, concurrency, export, lifecycle hooks
```

## Example prompts that trigger this skill

- *"Write a script to scrape job listings from example.com and save to JSON"*
- *"Crawl all product pages on this store and extract prices"*
- *"Bypass Cloudflare to get data from a protected site"*
- *"Build a spider that follows pagination and exports to CSV"*
- *"Migrate my BeautifulSoup scraper to something more robust"*

## How it works

When triggered, Claude follows a structured workflow:

1. **Understand the target** — What site? What data? One page or many?
2. **Choose the right fetcher** — Static HTTP, dynamic browser, or stealth anti-bot
3. **Inspect the page** — Fetch and analyze HTML structure
4. **Write the script** — Use Scrapling APIs with best practices
5. **Handle edge cases** — Pagination, empty results, rate limiting
6. **Export the data** — JSON, JSONL, CSV, or database

## Supported Scrapling features

- **Fetcher** — Fast HTTP requests with TLS fingerprint spoofing
- **DynamicFetcher** — Browser automation for JavaScript-rendered pages
- **StealthyFetcher** — Anti-bot bypass with Cloudflare solver
- **Spiders** — Concurrent multi-page crawlers with pause/resume
- **Adaptive scraping** — Selectors that survive website redesigns
- **Sessions** — Persistent cookies and shared browser instances
- **Proxy rotation** — Built-in proxy rotation across all fetchers

## Requirements

- Python 3.10+
- `pip install scrapling` (Claude will handle this in generated scripts)
- For browser features: `pip install "scrapling[fetchers]" && scrapling install`

## Manual install (without skills.sh)

If you prefer not to use `npx skills`, you can manually copy the skill files into your agent's skills directory:

### Claude Code
```bash
mkdir -p ~/.claude/skills/scrapling-skill
cp SKILL.md ~/.claude/skills/scrapling-skill/
cp -r references ~/.claude/skills/scrapling-skill/
```

### OpenCode
```bash
mkdir -p ~/.config/opencode/skills/scrapling-skill
cp SKILL.md ~/.config/opencode/skills/scrapling-skill/
cp -r references ~/.config/opencode/skills/scrapling-skill/
```

### Cursor
```bash
mkdir -p ~/.cursor/skills/scrapling-skill
cp SKILL.md ~/.cursor/skills/scrapling-skill/
cp -r references ~/.cursor/skills/scrapling-skill/
```

### Other agents
See the [skills.sh agent directory](https://github.com/vercel-labs/skills?tab=readme-ov-file#supported-agents) for your agent's specific skills path.

## Packaged skill file

You can also download the `.skill` file from the [releases page](https://github.com/dwk601/scrapling-skill/releases) and install it directly.

## License

BSD-3-Clause (same as Scrapling)

## Credits

Built for the [Scrapling](https://github.com/D4Vinci/Scrapling) web scraping framework by Karim Shoair.

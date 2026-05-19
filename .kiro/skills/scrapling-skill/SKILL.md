---
name: scrapling-skill
description: >-
  Write complete, production-ready web scraping scripts using the Scrapling
  library. Use this skill whenever the user wants to scrape a website, extract
  data from HTML, crawl multiple pages, bypass anti-bot protection, or build
  any kind of web scraper in Python — even if they don't explicitly mention
  "Scrapling", "scraping", or "crawler". This includes requests like
  "get data from a website", "extract prices from a store", "collect job
  listings", "download images from a gallery", "monitor a page for changes",
  or "automate browser tasks". Also use this skill when the user mentions
  BeautifulSoup, Scrapy, requests-html, Playwright scraping, or any Python
  web scraping task.
---

# Scrapling Skill

This skill helps you write complete Scrapling-based scraping scripts. Scrapling
is a modern Python web scraping framework that combines fast HTTP fetching,
stealthy browser automation, adaptive element tracking, and a Scrapy-like spider
system — all in one library.

## When to use this skill

Use this skill when the user asks you to:
- Scrape data from any website
- Extract structured data (products, jobs, articles, prices, etc.)
- Crawl multiple pages or follow links
- Bypass anti-bot protection (Cloudflare, etc.)
- Automate browser interactions for data extraction
- Build a scraping spider or crawler
- Migrate from BeautifulSoup or Scrapy

## Core workflow

When the user asks for a scraper, follow these steps:

1. **Understand the target** — What site? What data? One page or many?
2. **Choose the right fetcher** — See the decision tree below.
3. **Inspect the page** — Ask the user for the URL, then fetch it and inspect
   the HTML structure to write accurate selectors.
4. **Write the script** — Use Scrapling APIs. Start simple, then add features.
5. **Handle edge cases** — Pagination, empty results, rate limiting, retries.
6. **Export the data** — Save to JSON, JSONL, CSV, or a database.

## Fetcher decision tree

Scrapling provides three fetcher classes. Choose based on the target site:

```
Is the site static HTML (no JavaScript needed)?
  YES → Use Fetcher (fast HTTP, lowest overhead)
  NO  → Does the site have anti-bot protection (Cloudflare, CAPTCHA, WAF)?
          YES → Use StealthyFetcher (browser + stealth + anti-bot bypass)
          NO  → Use DynamicFetcher (browser for JS-rendered content)
```

| Fetcher | Speed | Stealth | JS | Best for |
|---------|-------|---------|----|----------|
| `Fetcher` | Fastest | Low | No | Static pages, APIs, simple HTML |
| `DynamicFetcher` | Medium | Medium | Yes | JS-rendered sites, SPA, small automation |
| `StealthyFetcher` | Medium | Highest | Yes | Protected sites, Cloudflare, WAF bypass |

**Default recommendation**: Start with `Fetcher`. If the data isn't in the raw
HTML, upgrade to `DynamicFetcher`. If you get blocked, use `StealthyFetcher`.

## Basic script template

```python
from scrapling.fetchers import Fetcher

# 1. Fetch the page
page = Fetcher.get('https://example.com')

# 2. Extract data with CSS selectors
for item in page.css('.product'):
    yield {
        'title': item.css('h2::text').get(),
        'price': item.css('.price::text').get(),
        'link': item.css('a::attr(href)').get(),
    }
```

## Key APIs

### Fetching

```python
from scrapling.fetchers import Fetcher, DynamicFetcher, StealthyFetcher

# Static fetch
page = Fetcher.get('https://example.com')
page = Fetcher.post('https://example.com/api', data={'key': 'value'})

# Dynamic fetch (browser)
page = DynamicFetcher.fetch('https://spa.example.com', headless=True)

# Stealthy fetch (anti-bot)
page = StealthyFetcher.fetch(
    'https://protected.example.com',
    solve_cloudflare=True,
    headless=True,
    timeout=60000,
)
```

### Selection

Scrapling supports CSS3, XPath, text search, regex, and filter-based finding:

```python
# CSS selectors
page.css('.product')           # All elements
page.css('.product')[0]        # First element
page.css('h1::text').get()     # Text extraction
page.css('a::attr(href)').getall()  # All attribute values

# XPath
page.xpath('//div[@class="product"]')

# Filter-based (easiest for beginners)
page.find_all('div', class_='product')
page.find('div', {'class': 'product'})
page.find_by_text('Add to Cart')
page.find_by_regex(r'\$[\d\.]+')

# Find similar elements (powerful for lists)
first = page.find_by_text('Product Name')
similar = first.find_similar()
```

### Spiders (multi-page crawling)

Use the spider system for crawling many pages with concurrency, retries, and
built-in export:

```python
from scrapling.spiders import Spider, Response

class JobSpider(Spider):
    name = "jobs"
    start_urls = ["https://example.com/jobs"]
    concurrent_requests = 4
    download_delay = 1.0

    async def parse(self, response: Response):
        for job in response.css('.job'):
            yield {
                'title': job.css('h2::text').get(),
                'company': job.css('.company::text').get(),
            }

        # Follow pagination
        next_page = response.css('a.next::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

# Run and export
result = JobSpider().start()
result.items.to_json('jobs.json')
```

### Sessions

For multiple requests with shared state (cookies, browser instance):

```python
from scrapling.fetchers import StealthySession

with StealthySession(headless=True, solve_cloudflare=True) as session:
    page1 = session.fetch('https://site1.com')
    page2 = session.fetch('https://site2.com')  # Reuses browser
```

## Advanced features

### Adaptive scraping

Enable `adaptive=True` to make selectors survive website redesigns:

```python
Fetcher.adaptive = True
page = Fetcher.get('https://example.com')

# Save element properties
products = page.css('.product', auto_save=True)

# Later, if the site changes, use the same selector:
products = page.css('.product', adaptive=True)  # Still works!
```

### Anti-bot with StealthyFetcher

```python
page = StealthyFetcher.fetch(
    'https://protected-site.com',
    solve_cloudflare=True,      # Auto-solve Cloudflare challenges
    block_webrtc=True,          # Prevent IP leak
    hide_canvas=True,           # Prevent canvas fingerprinting
    real_chrome=True,           # Use installed Chrome instead of Chromium
    proxy='http://user:pass@host:port',
)
```

### Spider lifecycle hooks

```python
class MySpider(Spider):
    async def on_start(self, resuming: bool = False):
        # Setup before crawl
        pass

    async def on_close(self):
        # Cleanup after crawl
        pass

    async def on_error(self, request, error):
        # Handle failed requests
        pass

    async def on_scraped_item(self, item: dict) -> dict | None:
        # Filter or enrich items
        return item
```

## Installation

```bash
pip install scrapling

# For fetchers and browsers:
pip install "scrapling[fetchers]"
scrapling install

# For everything (fetchers + AI + shell):
pip install "scrapling[all]"
scrapling install
```

## Reference files

For detailed documentation on specific topics, read the reference files bundled
with this skill:

- **`references/fetchers.md`** — All fetcher classes, sessions, proxy rotation,
  anti-bot options, and browser automation.
- **`references/parsing.md`** — Selection methods (CSS, XPath, `find_all`,
  `find_similar`, regex), generating selectors, and adaptive scraping.
- **`references/spiders.md`** — Spider architecture, concurrency, pause/resume,
  streaming, lifecycle hooks, statistics, and export formats.

## Tips for writing great scrapers

1. **Start simple** — Use `Fetcher` first. Only upgrade if needed.
2. **Inspect before coding** — Fetch the page and print `page.css('body').get()`
   to understand the structure.
3. **Use `find_all` for beginners** — It's more intuitive than raw CSS/XPath.
4. **Handle missing data** — Use `.get('')` with a default, not `.get()` alone.
5. **Respect robots.txt** — Set `robots_txt_obey = True` on spiders when
   appropriate.
6. **Add delays** — Use `download_delay` on spiders to be polite.
7. **Test selectors** — Run a quick script to verify selectors before building
   the full spider.
8. **Export early** — Use `result.items.to_json()` or `to_jsonl()` to verify
   output.
9. **Use sessions for multi-step flows** — Login, then navigate, then scrape.
10. **Enable adaptive for long-lived scrapers** — It saves maintenance time when
    sites change.

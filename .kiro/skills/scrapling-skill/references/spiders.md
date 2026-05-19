# Spiders Reference

Detailed reference for Scrapling's spider crawling framework.

## Table of Contents

1. [Basic Spider](#basic-spider)
2. [Running Spiders](#running-spiders)
3. [Following Links](#following-links)
4. [Requests and Responses](#requests-and-responses)
5. [Sessions in Spiders](#sessions-in-spiders)
6. [Concurrency Control](#concurrency-control)
7. [Pause and Resume](#pause-and-resume)
8. [Development Mode](#development-mode)
9. [Streaming](#streaming)
10. [Lifecycle Hooks](#lifecycle-hooks)
11. [Exporting Data](#exporting-data)
12. [Statistics](#statistics)
13. [Logging](#logging)
14. [Proxy and Blocking](#proxy-and-blocking)

---

## Basic Spider

Every spider needs three things: a name, start URLs, and a `parse()` method.

```python
from scrapling.spiders import Spider, Response

class QuotesSpider(Spider):
    name = "quotes"
    start_urls = ["https://quotes.toscrape.com"]

    async def parse(self, response: Response):
        for quote in response.css("div.quote"):
            yield {
                "text": quote.css("span.text::text").get(""),
                "author": quote.css("small.author::text").get(""),
            }
```

**Rules:**
- `parse()` must be an `async def` generator (uses `yield`)
- Callback methods must also be async generators
- `name` must be unique

## Running Spiders

```python
result = QuotesSpider().start()

# Access items
for item in result.items:
    print(item["text"])

# Check if crawl completed or was paused
print(result.completed)
print(result.paused)

# Statistics
print(result.stats.items_scraped)
print(result.stats.requests_count)
print(result.stats.elapsed_seconds)
```

**Start options:**
- `use_uvloop=True` — Use uvloop/winloop for better performance (must be installed separately)

## Following Links

```python
async def parse(self, response: Response):
    # Extract items from current page
    for quote in response.css("div.quote"):
        yield {"text": quote.css("span.text::text").get("")}

    # Follow "next page" link
    next_page = response.css("li.next a::attr(href)").get()
    if next_page:
        yield response.follow(next_page, callback=self.parse)

    # Follow links to detail pages with different callback
    for link in response.css("a.product-link::attr(href)").getall():
        yield response.follow(link, callback=self.parse_product)

async def parse_product(self, response: Response):
    yield {
        "name": response.css("h1::text").get(""),
        "price": response.css(".price::text").get(""),
    }
```

`response.follow()` automatically joins relative URLs and sets the `Referer` header.

## Requests and Responses

### Custom Start Requests

Instead of `start_urls`, override `start_requests()`:

```python
from scrapling.spiders import Request

async def start_requests(self):
    yield Request(
        "https://example.com/login",
        method="POST",
        data={"user": "admin", "pass": "secret"},
        callback=self.after_login,
    )
```

### Request Object

```python
Request(
    url="https://example.com",
    method="GET",           # or POST, PUT, DELETE, etc.
    headers={...},          # Custom headers
    cookies={...},          # Request cookies
    data={...},             # Form data (for POST)
    json={...},             # JSON body
    meta={...},             # Metadata passed to callback
    callback=self.parse,    # Processing callback
    priority=0,             # Higher = processed sooner
    dont_filter=False,      # Skip deduplication if True
)
```

### Response Object

Same as fetcher `Response` plus:

```python
response.url             # Final URL after redirects
response.follow(url, callback=...)  # Create follow-up request
```

## Sessions in Spiders

Use multiple fetcher types in a single spider by assigning session IDs:

```python
class MultiSessionSpider(Spider):
    name = "multi"
    start_urls = ["https://example.com"]

    async def parse(self, response: Response):
        # Route to stealth session for protected pages
        yield response.follow(
            "/protected",
            callback=self.parse_protected,
            session="stealth",
        )

    async def parse_protected(self, response: Response):
        # This request uses StealthyFetcher
        yield {"title": response.css("h1::text").get()}
```

Sessions are configured via the `sessions` dict or class attributes.

## Concurrency Control

```python
class MySpider(Spider):
    name = "my_spider"
    start_urls = ["https://example.com"]

    concurrent_requests = 4                # Global max concurrent
    concurrent_requests_per_domain = 2     # Per-domain limit (0 = unlimited)
    download_delay = 1.0                   # Seconds between requests
    robots_txt_obey = False                # Respect robots.txt
```

## Pause and Resume

Enable checkpoint-based persistence:

```python
spider = MySpider(crawldir="crawl_data/my_spider")
result = spider.start()

if result.paused:
    print("Crawl was paused. Run again to resume.")
```

**How it works:**
1. Press `Ctrl+C` once — graceful pause, saves checkpoint
2. Press `Ctrl+C` again — force stop immediately
3. Run again with same `crawldir` — resumes from checkpoint
4. Checkpoints auto-save every 5 minutes (configurable with `interval=`)

```python
# Save checkpoint every 2 minutes
spider = MySpider(crawldir="crawl_data", interval=120.0)
```

## Development Mode

Cache responses to disk so you can iterate on `parse()` without re-hitting servers:

```python
class MySpider(Spider):
    name = "my_spider"
    start_urls = ["https://example.com"]
    development_mode = True
    development_cache_dir = "/tmp/my_spider_cache"  # Optional override
```

**Warning:** Only for development. Cached responses never expire and bypass rate limiting.

To clear cache: delete the cache directory.

## Streaming

Yield items in real-time instead of collecting them:

```python
import anyio

async def main():
    spider = MySpider()
    async for item in spider.stream():
        print(f"Got: {item}")
        print(f"Items so far: {spider.stats.items_scraped}")

anyio.run(main)
```

Works with checkpoints too:

```python
async for item in MySpider(crawldir="crawl_data").stream():
    process(item)
```

## Lifecycle Hooks

### `on_start(resuming=False)`

Called before crawling begins:

```python
async def on_start(self, resuming: bool = False):
    if resuming:
        self.logger.info("Resuming from checkpoint!")
    else:
        self.logger.info("Starting fresh crawl")
```

### `on_close()`

Called after crawl finishes (completed or paused):

```python
async def on_close(self):
    self.logger.info("Spider shutting down")
    # Close DB connections, flush buffers, etc.
```

### `on_error(request, error)`

Called when a request fails:

```python
async def on_error(self, request, error):
    self.logger.error(f"Failed: {request.url} - {error}")
    # Log to error tracker, save failed URL for retry, etc.
```

### `on_scraped_item(item)`

Called for every item before adding to results. Return the item to keep it, or `None` to drop it:

```python
async def on_scraped_item(self, item: dict) -> dict | None:
    if not item.get("title"):
        return None  # Drop items without title
    item["scraped_at"] = "2026-01-01"
    return item
```

## Exporting Data

The `ItemList` from `result.items` has built-in export methods:

```python
result = MySpider().start()

# JSON (pretty-printed)
result.items.to_json("output.json", indent=True)

# JSON Lines (one object per line)
result.items.to_jsonl("output.jsonl")
```

Parent directories are created automatically.

## Statistics

```python
stats = result.stats

# Core stats
stats.items_scraped
stats.items_dropped
stats.requests_count
stats.failed_requests_count
stats.blocked_requests_count
stats.offsite_requests_count
stats.robots_disallowed_count
stats.response_bytes
stats.elapsed_seconds
stats.requests_per_second

# Detailed stats
stats.response_status_count        # {'status_200': 150, 'status_404': 3}
stats.domains_response_bytes       # {'example.com': 1234567}
stats.sessions_requests_count      # {'http': 120, 'stealth': 34}
stats.proxies                      # ['http://proxy1:8080', ...]
stats.cache_hits / stats.cache_misses
stats.log_levels_counter           # {'debug': 200, 'info': 50}
stats.concurrent_requests
stats.concurrent_requests_per_domain
stats.download_delay
stats.start_time / stats.end_time
stats.custom_stats                 # User-defined stats

# Export
stats.to_dict()
```

## Logging

```python
import logging

class MySpider(Spider):
    name = "my_spider"
    logging_level = logging.INFO      # Default: DEBUG
    log_file = "logs/my_spider.log"   # Default: None (console only)
    logging_format = "..."            # Custom format
    logging_date_format = "%Y-%m-%d %H:%M:%S"

    async def parse(self, response: Response):
        self.logger.info(f"Processing {response.url}")
        yield {"title": response.css("title::text").get("")}
```

Log file directory is created automatically.

## Proxy and Blocking

### Domain Filtering

```python
class MySpider(Spider):
    allowed_domains = {"example.com"}  # Subdomains matched automatically
```

Filtered requests count toward `stats.offsite_requests_count`.

### Robots.txt Compliance

```python
class PoliteSpider(Spider):
    robots_txt_obey = True
```

When enabled:
1. Pre-fetches robots.txt for all `start_urls` domains concurrently
2. Checks every request against `Disallow` rules
3. Respects `Crawl-delay` and `Request-rate` (takes max of directive and `download_delay`)

Does NOT affect concurrency settings — only adjusts delay between requests.

### Blocked Request Detection

The spider automatically detects blocked requests and retries them with customizable logic. Blocked requests count toward `stats.blocked_requests_count`.

### Using Proxies

```python
class ProxySpider(Spider):
    name = "proxy"
    start_urls = ["https://example.com"]

    # Per-request proxy via meta
    async def start_requests(self):
        yield Request(
            "https://example.com",
            meta={"proxy": "http://proxy1:8080"},
        )
```

Or use `ProxyRotator` with session configuration.

# Fetchers Reference

Detailed reference for Scrapling's fetcher classes, sessions, and related features.

## Table of Contents

1. [Fetcher Classes](#fetcher-classes)
2. [Response Object](#response-object)
3. [Sessions](#sessions)
4. [Proxy Rotation](#proxy-rotation)
5. [Anti-bot Options](#anti-bot-options)
6. [Browser Automation](#browser-automation)

---

## Fetcher Classes

### `Fetcher` — HTTP Requests

Fast, stealthy HTTP requests. Can impersonate browser TLS fingerprints and use HTTP/3.

```python
from scrapling.fetchers import Fetcher, AsyncFetcher

# Static methods — no initialization needed
page = Fetcher.get('https://example.com')
page = Fetcher.post('https://example.com/api', data={'key': 'value'})
page = Fetcher.fetch('https://example.com')  # Alias for GET

# Async
page = await AsyncFetcher.get('https://example.com')
```

**Key arguments:**
- `headers` — Custom request headers
- `cookies` — Request cookies
- `timeout` — Request timeout in seconds
- `proxy` — Proxy URL
- `follow_redirects` — Whether to follow redirects (default: True)
- `verify` — SSL certificate verification

### `DynamicFetcher` — Browser Automation

Fetches JavaScript-rendered pages using a headless browser (Chromium/Chrome via Playwright).

```python
from scrapling.fetchers import DynamicFetcher, AsyncDynamicFetcher

page = DynamicFetcher.fetch('https://spa.example.com', headless=True)
```

**Key arguments:**
- `headless` — Run browser hidden (default: True)
- `network_idle` — Wait until no network activity for 500ms
- `load_dom` — Wait for DOM content loaded (default: True)
- `wait` — Extra wait time in ms after load
- `wait_selector` — Wait for a CSS selector to appear
- `wait_selector_state` — State to wait for: `attached`, `detached`, `visible`, `hidden`
- `page_action` — Function for custom automation (receives Playwright `Page`)
- `page_setup` — Function run before navigation
- `disable_resources` — Block fonts, images, media, etc. for speed
- `proxy` — Proxy URL or dict with `server`, `username`, `password`
- `timeout` — Operation timeout in ms (default: 30000)
- `real_chrome` — Use installed Chrome instead of bundled Chromium
- `capture_xhr` — Regex pattern to capture XHR/fetch responses (access via `response.captured_xhr`)

### `StealthyFetcher` — Anti-bot Bypass

Everything `DynamicFetcher` does, plus advanced stealth to bypass anti-bot systems.

```python
from scrapling.fetchers import StealthyFetcher, AsyncStealthyFetcher

page = StealthyFetcher.fetch(
    'https://protected.example.com',
    solve_cloudflare=True,
    headless=True,
    timeout=60000,
)
```

**Additional arguments over DynamicFetcher:**
- `solve_cloudflare` — Auto-detect and solve all Cloudflare challenge types
- `block_webrtc` — Force WebRTC to respect proxy settings
- `hide_canvas` — Add random noise to canvas operations
- `allow_webgl` — Enable WebGL support (default: True; disabling may trigger WAF)

**Important:** When using `solve_cloudflare`, set `timeout` to at least 60000 ms.

---

## Response Object

All fetchers return a `Response` object, which is a `Selector` with extra metadata:

```python
page = Fetcher.get('https://example.com')

# HTTP metadata
page.status          # HTTP status code
page.reason          # Status message
page.cookies         # Response cookies dict
page.headers         # Response headers
page.request_headers # Request headers
page.history         # Redirection history
page.body            # Raw response bytes
page.encoding        # Response encoding
page.meta            # Response metadata (e.g., proxy used)

# XHR capture (when capture_xhr is enabled)
page.captured_xhr    # List of captured XHR/fetch responses
```

---

## Sessions

Sessions keep the browser or HTTP client alive across multiple requests, preserving cookies and state.

### HTTP Sessions

```python
from scrapling.fetchers import FetcherSession, AsyncFetcherSession

with FetcherSession() as session:
    page1 = session.get('https://example.com/login')
    page2 = session.post('https://example.com/login', data={'user': 'x', 'pass': 'y'})
    page3 = session.get('https://example.com/dashboard')
```

### Stealthy Sessions

```python
from scrapling.fetchers import StealthySession, AsyncStealthySession

with StealthySession(
    headless=True,
    solve_cloudflare=True,
    block_webrtc=True,
) as session:
    page1 = session.fetch('https://site1.com')
    page2 = session.fetch('https://site2.com')
```

**Session-specific arguments:**
- `user_data_dir` — Path to persist browser data (cookies, localStorage)
- `max_pages` — Rotating pool of browser tabs (async sessions only)

### Async Session with Concurrent Requests

```python
import asyncio
from scrapling.fetchers import AsyncStealthySession

async def scrape_multiple():
    async with AsyncStealthySession(max_pages=3) as session:
        pages = await asyncio.gather(
            session.fetch('https://site1.com'),
            session.fetch('https://site2.com'),
            session.fetch('https://site3.com'),
        )
        return pages

asyncio.run(scrape_multiple())
```

---

## Proxy Rotation

Built-in proxy rotation with cyclic or custom strategies:

```python
from scrapling.fetchers import Fetcher
from scrapling import ProxyRotator

rotator = ProxyRotator([
    'http://proxy1:8080',
    'http://user:pass@proxy2:8080',
    'socks5://proxy3:1080',
])

page = Fetcher.get('https://example.com', proxy_rotator=rotator)
```

Works with all fetcher types and sessions.

---

## Anti-bot Options

When using `StealthyFetcher`, these stealth features are applied automatically or on demand:

| Feature | How to enable | What it does |
|---------|--------------|--------------|
| Cloudflare solver | `solve_cloudflare=True` | Auto-solves all Cloudflare challenge types |
| WebRTC blocking | `block_webrtc=True` | Prevents local IP leak through WebRTC |
| Canvas noise | `hide_canvas=True` | Adds random noise to canvas fingerprinting |
| Real Chrome | `real_chrome=True` | Uses installed Chrome instead of bundled Chromium |
| Google referer | `google_search=True` (default) | Sets Google as referer |
| Proxy | `proxy=...` | Routes traffic through proxy |
| DNS over HTTPS | `dns_over_https=True` | Prevents DNS leaks when using proxies |
| Domain blocking | `blocked_domains={'ads.com'}` | Blocks requests to specific domains |
| Ad blocking | `block_ads=True` | Blocks ~3,500 known ad/tracker domains |

### Browser Automation with `page_action`

For sites requiring interaction (scrolling, clicking, form filling):

```python
from playwright.sync_api import Page

def interact(page: Page):
    page.click('button.load-more')
    page.wait_for_timeout(2000)
    page.mouse.wheel(0, 500)

page = StealthyFetcher.fetch(
    'https://example.com',
    page_action=interact,
    wait_selector='.loaded-content',
)
```

For async fetchers, the function must also be async and use `playwright.async_api.Page`.

---

## Parser Configuration

Configure the parser globally for a fetcher class:

```python
from scrapling.fetchers import Fetcher

Fetcher.configure(adaptive=True, keep_comments=False)
# or
Fetcher.adaptive = True
Fetcher.keep_comments = False

Fetcher.display_config()  # Show current config
```

Available config options: `adaptive`, `adaptive_domain`, `huge_tree`, `keep_comments`, `keep_cdata`, `storage`, `storage_args`.

For per-request config, pass `selector_config` as a dict to any fetch method.

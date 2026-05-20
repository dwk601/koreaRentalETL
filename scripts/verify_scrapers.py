"""Standalone verification that each active scraper can fetch list pages and detail pages.

Bypasses DB / Redis / audit logging. Calls crawl_list_pages() directly and fetch_detail()
on the first listing of each source.

Detects when a scraper silently falls back to the test fixture (the source scrapers
catch fetch errors and read tests/fixtures/html/<source>/list_page_1.html). Those
listings are NOT live data, so we flag them.
"""

from __future__ import annotations

import logging
import sys
import time
import traceback
from typing import Any

from korean_rental_etl.extract.scraper_factory import ScraperFactory
from korean_rental_etl.extract.source_config import active_sources, load_sources

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Reduce noise from libraries
logging.getLogger("scrapling").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("playwright").setLevel(logging.WARNING)


SAMPLE_LIMIT = 5  # only collect this many listings to keep the run quick


class FixtureFallbackDetector(logging.Handler):
    """Captures the 'Could not fetch list page, using fixture fallback' warning."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.fixture_fallback = False
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        self.messages.append(msg)
        if "fixture fallback" in msg:
            self.fixture_fallback = True


def verify_source(src_config: Any) -> dict[str, Any]:
    """Run crawl_list_pages() (limited) and fetch_detail() once for the source.

    Returns a result dict with status + diagnostics.
    """
    name = src_config.name
    result: dict[str, Any] = {
        "source": name,
        "fetcher": src_config.fetcher,
        "url": src_config.full_url,
        "listings_collected": 0,
        "sample_listings": [],
        "list_ok": False,
        "detail_ok": False,
        "detail_status": None,
        "detail_html_len": 0,
        "fixture_fallback": False,
        "warnings": [],
        "error": None,
        "list_duration_s": None,
        "detail_duration_s": None,
    }

    # Attach a detector to the source's scraper logger
    detector = FixtureFallbackDetector()
    scraper_logger = logging.getLogger(f"korean_rental_etl.extract.scrapers.{name}")
    scraper_logger.addHandler(detector)
    scraper_logger.setLevel(logging.WARNING)

    try:
        try:
            scraper = ScraperFactory.create(src_config, source_id=1)
        except Exception as e:
            result["error"] = f"factory: {e}"
            return result

        # 1) crawl list pages (sample only)
        listings: list[dict[str, Any]] = []
        t0 = time.time()
        try:
            for i, listing in enumerate(scraper.crawl_list_pages()):
                listings.append(listing)
                if i + 1 >= SAMPLE_LIMIT:
                    break
            result["list_duration_s"] = round(time.time() - t0, 2)
            result["listings_collected"] = len(listings)
            result["sample_listings"] = [
                {"title": l.get("title", "")[:80], "url": l.get("url", "")} for l in listings[:3]
            ]
            result["list_ok"] = len(listings) > 0 and not detector.fixture_fallback
        except Exception as e:
            result["list_duration_s"] = round(time.time() - t0, 2)
            result["error"] = f"crawl_list_pages: {e}\n{traceback.format_exc()}"
            return result
        finally:
            result["fixture_fallback"] = detector.fixture_fallback
            result["warnings"] = list(detector.messages)

        if not listings:
            result["error"] = "list page returned 0 listings"
            return result

        if detector.fixture_fallback:
            result["error"] = "fell back to test fixture - live fetch failed silently"
            # Still try the detail fetch on the fixture URL just to see the failure mode
        # 2) fetch first detail page
        sample_url = listings[0]["url"]
        t1 = time.time()
        try:
            detail = scraper.fetch_detail(sample_url)
            result["detail_duration_s"] = round(time.time() - t1, 2)
            html = detail.get("html", "") or ""
            result["detail_status"] = detail.get("status")
            result["detail_html_len"] = len(html)
            result["detail_ok"] = bool(html) and (detail.get("status") in (None, 200))
        except Exception as e:
            result["detail_duration_s"] = round(time.time() - t1, 2)
            result["error"] = (result.get("error") or "") + f" | fetch_detail({sample_url}): {e}"
            return result

    finally:
        scraper_logger.removeHandler(detector)

    return result


def fmt_result(r: dict[str, Any]) -> str:
    status = "PASS" if r["list_ok"] and r["detail_ok"] else "FAIL"
    lines = [
        f"=== {r['source']} [{status}] ({r['fetcher']}) ===",
        f"  URL:                {r['url']}",
        f"  list_ok:            {r['list_ok']}  (listings={r['listings_collected']}, "
        f"took={r['list_duration_s']}s)",
        f"  detail_ok:          {r['detail_ok']}  (status={r['detail_status']}, "
        f"html_len={r['detail_html_len']}, took={r['detail_duration_s']}s)",
        f"  fixture_fallback:   {r['fixture_fallback']}",
    ]
    if r["sample_listings"]:
        lines.append("  sample listings:")
        for s in r["sample_listings"]:
            lines.append(f"    - {s['title'] or '(no title)'} -> {s['url']}")
    if r["error"]:
        lines.append(f"  ERROR: {r['error'].splitlines()[0]}")
    return "\n".join(lines)


def main() -> int:
    config = load_sources()
    sources = active_sources(config)

    print(f"Verifying {len(sources)} active sources...\n")

    results: list[dict[str, Any]] = []
    for src in sources:
        print(f"--- Running {src.name} ({src.fetcher}) ---", flush=True)
        try:
            r = verify_source(src)
        except Exception as e:
            r = {
                "source": src.name,
                "fetcher": src.fetcher,
                "url": src.full_url,
                "list_ok": False,
                "detail_ok": False,
                "listings_collected": 0,
                "sample_listings": [],
                "detail_status": None,
                "detail_html_len": 0,
                "fixture_fallback": False,
                "warnings": [],
                "list_duration_s": None,
                "detail_duration_s": None,
                "error": f"unhandled: {e}",
            }
        results.append(r)
        print(fmt_result(r), flush=True)
        print(flush=True)

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(1 for r in results if r["list_ok"] and r["detail_ok"])
    print(f"{passed}/{len(results)} sources passed full live verification\n")
    for r in results:
        flag = "PASS" if r["list_ok"] and r["detail_ok"] else "FAIL"
        list_flag = "L+" if r["list_ok"] else "L-"
        det_flag = "D+" if r["detail_ok"] else "D-"
        fix = " [FIXTURE]" if r["fixture_fallback"] else ""
        err = ""
        if not (r["list_ok"] and r["detail_ok"]) and r["error"]:
            err = f" :: {r['error'].splitlines()[0][:120]}"
        print(
            f"  [{flag}] {r['source']:20s} {list_flag} {det_flag}  "
            f"listings={r['listings_collected']:>3} html={r['detail_html_len']:>7}b{fix}{err}"
        )

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())

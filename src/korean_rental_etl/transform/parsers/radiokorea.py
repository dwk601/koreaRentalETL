"""Radio Korea parser."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from korean_rental_etl.transform.parsers._common import (
    compute_content_hash,
    extract_body_text,
    extract_labelled_field,
    extract_text,
    extract_text_first_match,
    infer_location,
)
from korean_rental_etl.transform.parsers.base_parser import BaseParser


class RadiokoreaParser(BaseParser):
    """Parser for m.radiokorea.com/c_realestate."""

    def __init__(self) -> None:
        super().__init__("radiokorea")

    def parse_detail(self, html: str, url: str) -> dict[str, Any]:
        """Parse Radio Korea detail page."""
        soup = BeautifulSoup(html, "html.parser")

        # Extract listing ID from wr_id query param
        source_listing_id = ""
        match = re.search(r"wr_id=(\d+)", url)
        if match:
            source_listing_id = match.group(1)

        # Title extraction with fallbacks
        title_selectors = [
            ".realestate_over h1",
            "#contents-left-center h1",
            ".realestate_view h1",
            "h1",
        ]
        title_ko = extract_text_first_match(soup, title_selectors)
        if not title_ko:
            t = soup.find("title")
            title_ko = t.get_text(strip=True) if t else ""
        # Strip ' | 라디오코리아' suffix
        for sfx in [" | 라디오코리아"]:
            if title_ko.endswith(sfx):
                title_ko = title_ko[: -len(sfx)].strip()

        # Body extraction with fallbacks
        body_selectors = [
            ".realestate_over",
            "#contents-left-center",
            ".realestate_view .view_content",
        ]
        body_ko = extract_body_text(soup, body_selectors)
        if not body_ko:
            body_el = soup.find("body")
            body_ko = extract_text(body_el) if body_el else ""

        # Extract labelled fields from body text
        labelled_location = extract_labelled_field(body_ko, ["위치", "Location"])
        raw_location = infer_location(title_ko, body_ko, labelled_location)
        raw_price = "\n".join(
            [
                extract_labelled_field(body_ko, ["월세"]),
                extract_labelled_field(body_ko, ["보증금"]),
                extract_labelled_field(body_ko, ["전세"]),
                extract_labelled_field(body_ko, ["Rent"]),
            ]
        ).strip()
        raw_price = "\n".join(line for line in raw_price.split("\n") if line)

        # Date from body text
        raw_posted_at = extract_labelled_field(body_ko, ["작성일", "Posted", "Date"])

        # Contact from labelled field
        contact_block = extract_labelled_field(body_ko, ["연락처", "이메일", "카카오", "Contact"])

        return {
            "title_ko": title_ko,
            "body_ko": body_ko,
            "raw_price": raw_price,
            "raw_location": raw_location,
            "raw_posted_at": raw_posted_at,
            "contact_block": contact_block,
            "source_listing_id": source_listing_id,
            "url": url,
            "content_hash": compute_content_hash(html),
        }

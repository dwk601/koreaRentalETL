"""Illinois KSA parser."""

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


class IllinoisksaParser(BaseParser):
    """Parser for illinoisksa.org/housing (KBoard plugin)."""

    def __init__(self) -> None:
        super().__init__("illinoisksa")

    def parse_detail(self, html: str, url: str) -> dict[str, Any]:
        """Parse Illinois KSA detail page."""
        soup = BeautifulSoup(html, "html.parser")

        # Extract listing ID from uid query param
        source_listing_id = ""
        match = re.search(r"uid=(\d+)", url)
        if match:
            source_listing_id = match.group(1)

        # Title extraction
        title_selectors = [".kboard-title h1", "h1"]
        title_ko = extract_text_first_match(soup, title_selectors)

        # Body extraction
        body_selectors = [".kboard-content .content-view", ".kboard-content"]
        body_ko = extract_body_text(soup, body_selectors)
        if not body_ko:
            body_el = soup.select_one(".kboard-content")
            body_ko = extract_text(body_el) if body_el else ""

        # Date from detail attribute
        raw_posted_at = ""
        date_el = soup.select_one(".detail-attr.detail-date")
        if date_el:
            date_text = extract_text(date_el)
            # Strip "작성일" prefix
            for prefix in ["작성일:", "작성일"]:
                if date_text.startswith(prefix):
                    date_text = date_text[len(prefix) :].strip()
            raw_posted_at = date_text

        # Extract labelled fields from body text
        labelled_location = extract_labelled_field(body_ko, ["위치", "Location", "주소"])
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

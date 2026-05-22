"""Ktown Koreadaily parser.

ktown.koreadaily.com is an ASP.NET (Web Forms) classifieds board. Detail
pages expose stable element ids of the form `MainContent_lbl_*` that map
directly to the listing's structured fields, so we read those instead of
selectors that are sensitive to layout changes.

Detail URLs look like
https://ktown.koreadaily.com/ad_rent/rentview?data=<id> where <id> is the
listing id.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from korean_rental_etl.transform.parsers._common import (
    compute_content_hash,
    extract_text,
)
from korean_rental_etl.transform.parsers.base_parser import BaseParser


def _id_text(soup: BeautifulSoup, element_id: str) -> str:
    return extract_text(soup.find(id=element_id))


class KtownKoreadailyParser(BaseParser):
    """Parser for ktown.koreadaily.com/ad_rent/rentview."""

    def __init__(self) -> None:
        super().__init__("ktown_koreadaily")

    def parse_detail(self, html: str, url: str) -> dict[str, Any]:
        """Parse Ktown Koreadaily detail page."""
        soup = BeautifulSoup(html, "html.parser")

        # Listing id from ?data=<id> query param.
        source_listing_id = ""
        match = re.search(r"[?&]data=([^&#]+)", url)
        if match:
            source_listing_id = match.group(1)

        title_ko = _id_text(soup, "MainContent_lbl_title")
        raw_posted_at = _id_text(soup, "MainContent_lbl_boardregdate")
        raw_price = _id_text(soup, "MainContent_lbl_pay") or _id_text(soup, "MainContent_lbl_pay2")

        city = _id_text(soup, "MainContent_lbl_city")
        state = _id_text(soup, "MainContent_lbl_state")
        raw_location = f"{city}, {state}" if city and state else city or state

        # Build a body summary from the structured fields. ktown listings on
        # this board are short ads; the title + structured fields ARE the
        # body, there's no separate description blob.
        category = _id_text(soup, "MainContent_lbl_joblist")
        bedrooms = _id_text(soup, "MainContent_lbl_bedroom")
        bathrooms = _id_text(soup, "MainContent_lbl_bathroom")
        size = _id_text(soup, "MainContent_lbl_sq")

        body_lines = [title_ko] if title_ko else []
        if category:
            body_lines.append(f"형태: {category}")
        if bedrooms and bedrooms != "0":
            body_lines.append(f"Bedrooms: {bedrooms}")
        if bathrooms and bathrooms != "0":
            body_lines.append(f"Bathrooms: {bathrooms}")
        if size and size not in ("0 sq ft", "0"):
            body_lines.append(f"크기: {size}")
        body_ko = "\n".join(body_lines)

        # Contact block
        contact_parts = []
        phone = _id_text(soup, "MainContent_lbl_telnum")
        if phone:
            contact_parts.append(f"전화: {phone}")
        writer = _id_text(soup, "MainContent_lbl_writer")
        company = _id_text(soup, "MainContent_lbl_companyname")
        if writer:
            contact_parts.append(f"작성자: {writer}")
        if company:
            contact_parts.append(f"회사: {company}")
        contact_block = "\n".join(contact_parts)

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

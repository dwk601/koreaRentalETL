"""GTKSA parser."""

from bs4 import BeautifulSoup

from korean_rental_etl.transform.parsers._common import (
    compute_content_hash,
    extract_contact_block,
    extract_text,
)
from korean_rental_etl.transform.parsers.base_parser import BaseParser


class GTKSAParser(BaseParser):
    """Parser for gtksa.net/bbs/board.php?bo_table=rent."""

    def __init__(self):
        super().__init__("gtksa")

    def parse_detail(self, html: str, url: str) -> dict:
        """Parse GTKSA detail page."""
        soup = BeautifulSoup(html, "html.parser")

        source_listing_id = url.split("wr_id=")[-1].split("&")[0] if "wr_id=" in url else "unknown"

        title_elem = soup.select_one("h1.title, .view-subject, h2")
        title_ko = extract_text(title_elem) if title_elem else ""

        body_elem = soup.select_one(".view-content, .content, .body")
        body_ko = extract_text(body_elem) if body_elem else ""

        price_elem = soup.select_one(".price, [class*='price']")
        raw_price = extract_text(price_elem) if price_elem else ""

        location_elem = soup.select_one(".location, .address, [class*='location']")
        raw_location = extract_text(location_elem) if location_elem else ""

        date_elem = soup.select_one(".date, .view-date, [class*='date']")
        raw_posted_at = extract_text(date_elem) if date_elem else ""

        contact_elem = soup.select_one(".contact, .phone, [class*='contact']")
        contact_block = extract_contact_block(contact_elem)

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

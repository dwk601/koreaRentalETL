"""SVKoreans parser.

The svkoreans.com community board uses gnuboard5 with a Bootstrap 4 theme.
Detail pages have these article sections:
  - h1#bo_v_title — listing title
  - section#bo_v_info time[datetime] — ISO posted date
  - section#bo_v_con — Korean+English description blob
  - section#bo_v_atc — small unnamed <table> with labelled meta fields
    (가격, 지역/위치, 전화번호, 이메일, 마감일).

Detail URLs look like https://svkoreans.com/rent_housing/<id>?page=<N> where
<id> is the listing id and <N> is the list-page that surfaced it.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from korean_rental_etl.transform.parsers._common import (
    compute_content_hash,
    extract_text,
)
from korean_rental_etl.transform.parsers.base_parser import BaseParser


def _parse_meta_table(container: Tag | None) -> dict[str, str]:
    """Parse the small unnamed <table> in #bo_v_atc into a {label: value} dict.

    Expected structure per row:
      <tr><td><span>label</span></td><td><span class="na-bar"></span> value</td></tr>
    """
    meta: dict[str, str] = {}
    if not container:
        return meta
    for table in container.find_all("table"):
        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 2:
                continue
            label = extract_text(cells[0])
            # Value cell starts with a <span class="na-bar"></span> separator;
            # strip it before reading the text.
            value_cell = cells[1]
            for sep in value_cell.find_all("span", class_="na-bar"):
                sep.extract()
            value = extract_text(value_cell)
            if label:
                meta[label] = value
    return meta


def _extract_description(content_el: Tag | None) -> str:
    """Return the listing description from #bo_v_con as multi-line text."""
    if not content_el:
        return ""
    clone = BeautifulSoup(str(content_el), "html.parser")
    # If any tables snuck in (defensive), drop them.
    for table in clone.find_all("table"):
        table.decompose()
    for br in clone.find_all("br"):
        br.replace_with("\n")
    text = clone.get_text("\n", strip=True)
    # Collapse 3+ blank lines but preserve paragraph breaks.
    return re.sub(r"\n{3,}", "\n\n", text)


class SVKoreansParser(BaseParser):
    """Parser for svkoreans.com/rent_housing."""

    def __init__(self) -> None:
        super().__init__("svkoreans")

    def parse_detail(self, html: str, url: str) -> dict[str, Any]:
        """Parse svkoreans detail page."""
        soup = BeautifulSoup(html, "html.parser")

        # Listing id is the path segment after /rent_housing/, NOT the
        # ?page= query value. e.g. /rent_housing/1634?page=1 -> 1634.
        source_listing_id = ""
        match = re.search(r"/rent_housing/(\d+)", url)
        if match:
            source_listing_id = match.group(1)

        # Title
        title_ko = extract_text(soup.select_one("h1#bo_v_title"))

        # Posted date — prefer the <time datetime="..."> attribute (ISO 8601
        # with offset) over its rendered text.
        raw_posted_at = ""
        time_el = soup.select_one("#bo_v_info time[datetime]")
        if time_el:
            raw_posted_at = time_el.get("datetime") or extract_text(time_el)
        else:
            raw_posted_at = extract_text(soup.select_one("#bo_v_info time"))

        # Body description and structured meta come from different sections.
        body_ko = _extract_description(soup.select_one("#bo_v_con"))
        meta = _parse_meta_table(soup.select_one("#bo_v_atc"))

        raw_price = meta.get("가격", "")
        raw_location = meta.get("지역/위치", "") or meta.get("위치", "")

        # Compose contact_block from phone + email when present.
        contact_parts = []
        phone = meta.get("전화번호", "")
        email = meta.get("이메일", "")
        if phone:
            contact_parts.append(f"전화: {phone}")
        if email:
            contact_parts.append(f"이메일: {email}")
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

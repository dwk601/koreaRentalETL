"""Base parser for all sources."""

from abc import ABC, abstractmethod


class BaseParser(ABC):
    """Abstract base for per-source HTML parsers."""

    def __init__(self, source_name: str):
        self.source_name = source_name

    @abstractmethod
    def parse_detail(self, html: str, url: str) -> dict:
        """Parse detail page HTML.

        Returns dict with:
        - title_ko, body_ko, raw_price, raw_location, raw_posted_at, contact_block
        - source_listing_id, url, content_hash
        """
        pass

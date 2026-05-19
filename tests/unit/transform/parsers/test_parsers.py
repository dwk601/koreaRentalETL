"""Unit tests for per-source parsers."""

from pathlib import Path

import pytest

from korean_rental_etl.transform.parsers.gtksa import GTKSAParser
from korean_rental_etl.transform.parsers.ktown_koreadaily import KtownKoreadailyParser
from korean_rental_etl.transform.parsers.missyusa import MissyusaParser
from korean_rental_etl.transform.parsers.radiokorea import RadiokoreaParser
from korean_rental_etl.transform.parsers.svkoreans import SVKoreansParser


@pytest.fixture
def fixture_dir():
    """Return path to HTML fixtures."""
    return Path(__file__).parent.parent.parent.parent / "fixtures" / "html"


class TestSVKoreansParser:
    """Test SVKoreans parser."""

    def test_parse_detail(self, fixture_dir):
        """Parse svkoreans detail page."""
        html_file = fixture_dir / "svkoreans" / "detail_12345.html"
        if not html_file.exists():
            pytest.skip("Fixture not found")

        html = html_file.read_text()
        parser = SVKoreansParser()
        result = parser.parse_detail(html, "https://svkoreans.com/rent_housing/12345")

        assert result["source_listing_id"] == "12345"
        assert result["url"] == "https://svkoreans.com/rent_housing/12345"
        assert "content_hash" in result
        assert len(result["content_hash"]) == 16


class TestGTKSAParser:
    """Test GTKSA parser."""

    def test_parse_detail(self, fixture_dir):
        """Parse GTKSA detail page."""
        html_file = fixture_dir / "gtksa" / "detail_1001.html"
        if not html_file.exists():
            pytest.skip("Fixture not found")

        html = html_file.read_text()
        parser = GTKSAParser()
        result = parser.parse_detail(
            html, "https://gtksa.net/bbs/board.php?bo_table=rent&wr_id=1001"
        )

        assert result["source_listing_id"] == "1001"
        assert "content_hash" in result


class TestMissyusaParser:
    """Test Missyusa parser."""

    def test_parse_detail(self, fixture_dir):
        """Parse Missyusa detail page."""
        html_file = fixture_dir / "missyusa" / "detail_m2001.html"
        if not html_file.exists():
            pytest.skip("Fixture not found")

        html = html_file.read_text()
        parser = MissyusaParser()
        result = parser.parse_detail(html, "https://missyusa.com/town9/2001")

        assert result["source_listing_id"] == "2001"
        assert "content_hash" in result


class TestKtownKoreadailyParser:
    """Test Ktown Koreadaily parser."""

    def test_parse_detail(self, fixture_dir):
        """Parse Ktown Koreadaily detail page."""
        html_file = fixture_dir / "ktown_koreadaily" / "detail_k3001.html"
        if not html_file.exists():
            pytest.skip("Fixture not found")

        html = html_file.read_text()
        parser = KtownKoreadailyParser()
        result = parser.parse_detail(html, "https://ktown.koreadaily.com/ad_rent/rentlist/3001")

        assert result["source_listing_id"] == "3001"
        assert "content_hash" in result


class TestRadiokoreaParser:
    """Test Radio Korea parser."""

    def test_parse_detail(self, fixture_dir):
        """Parse Radio Korea detail page."""
        html_file = fixture_dir / "radiokorea" / "detail_r4001.html"
        if not html_file.exists():
            pytest.skip("Fixture not found")

        html = html_file.read_text()
        parser = RadiokoreaParser()
        result = parser.parse_detail(html, "https://m.radiokorea.com/c_realestate/4001")

        assert result["source_listing_id"] == "4001"
        assert "content_hash" in result

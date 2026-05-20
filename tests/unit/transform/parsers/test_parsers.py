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

    def test_detail_12345(self, fixture_dir):
        """Parse svkoreans detail_12345.html."""
        html_file = fixture_dir / "svkoreans" / "detail_12345.html"
        html = html_file.read_text()
        parser = SVKoreansParser()
        result = parser.parse_detail(html, "https://svkoreans.com/rent_housing/12345")

        assert result["source_listing_id"] == "12345"
        assert "[LA]" in result["title_ko"]
        assert "다운타운" in result["title_ko"]
        assert "월세" in result["title_ko"]
        assert "$1,500" in result["title_ko"]
        assert "LA 다운타운 7th Street" in result["raw_location"]
        assert "$1,500" in result["raw_price"]
        assert "$3,000" in result["raw_price"]
        assert "213-555-1234" in result["contact_block"]
        assert "2024년 5월 1일" in result["raw_posted_at"]
        assert len(result["content_hash"]) == 64

    def test_detail_12346(self, fixture_dir):
        """Parse svkoreans detail_12346.html."""
        html_file = fixture_dir / "svkoreans" / "detail_12346.html"
        html = html_file.read_text()
        parser = SVKoreansParser()
        result = parser.parse_detail(html, "https://svkoreans.com/rent_housing/12346")

        assert result["source_listing_id"] == "12346"
        assert "어바인" in result["title_ko"]
        assert "$2,800" in result["raw_price"]
        assert "$3,000" in result["raw_price"]
        assert "949-555-5678" in result["contact_block"]

    def test_detail_12347(self, fixture_dir):
        """Parse svkoreans detail_12347.html."""
        html_file = fixture_dir / "svkoreans" / "detail_12347.html"
        html = html_file.read_text()
        parser = SVKoreansParser()
        result = parser.parse_detail(html, "https://svkoreans.com/rent_housing/12347")

        assert result["source_listing_id"] == "12347"
        assert "전세" in result["title_ko"]
        assert "$2,500" in result["raw_price"]
        assert "sfrental" in result["contact_block"]


class TestGTKSAParser:
    """Test GTKSA parser."""

    def test_detail_1001(self, fixture_dir):
        """Parse GTKSA detail_1001.html."""
        html_file = fixture_dir / "gtksa" / "detail_1001.html"
        html = html_file.read_text()
        parser = GTKSAParser()
        result = parser.parse_detail(
            html, "https://gtksa.net/bbs/board.php?bo_table=rent&wr_id=1001"
        )

        assert result["source_listing_id"] == "1001"
        assert len(result["content_hash"]) == 64

    def test_detail_1002(self, fixture_dir):
        """Parse GTKSA detail_1002.html."""
        html_file = fixture_dir / "gtksa" / "detail_1002.html"
        html = html_file.read_text()
        parser = GTKSAParser()
        result = parser.parse_detail(
            html, "https://gtksa.net/bbs/board.php?bo_table=rent&wr_id=1002"
        )

        assert result["source_listing_id"] == "1002"
        assert len(result["content_hash"]) == 64

    def test_detail_1003(self, fixture_dir):
        """Parse GTKSA detail_1003.html."""
        html_file = fixture_dir / "gtksa" / "detail_1003.html"
        html = html_file.read_text()
        parser = GTKSAParser()
        result = parser.parse_detail(
            html, "https://gtksa.net/bbs/board.php?bo_table=rent&wr_id=1003"
        )

        assert result["source_listing_id"] == "1003"
        assert len(result["content_hash"]) == 64


class TestMissyusaParser:
    """Test Missyusa parser."""

    def test_detail_m2001(self, fixture_dir):
        """Parse Missyusa detail_m2001.html."""
        html_file = fixture_dir / "missyusa" / "detail_m2001.html"
        html = html_file.read_text()
        parser = MissyusaParser()
        result = parser.parse_detail(html, "https://missyusa.com/town9?idx=2001")

        assert result["source_listing_id"] == "2001"
        assert len(result["content_hash"]) == 64

    def test_detail_m2002(self, fixture_dir):
        """Parse Missyusa detail_m2002.html."""
        html_file = fixture_dir / "missyusa" / "detail_m2002.html"
        html = html_file.read_text()
        parser = MissyusaParser()
        result = parser.parse_detail(html, "https://missyusa.com/town9?idx=2002")

        assert result["source_listing_id"] == "2002"
        assert len(result["content_hash"]) == 64

    def test_detail_m2003(self, fixture_dir):
        """Parse Missyusa detail_m2003.html."""
        html_file = fixture_dir / "missyusa" / "detail_m2003.html"
        html = html_file.read_text()
        parser = MissyusaParser()
        result = parser.parse_detail(html, "https://missyusa.com/town9?idx=2003")

        assert result["source_listing_id"] == "2003"
        assert len(result["content_hash"]) == 64


class TestKtownKoreadailyParser:
    """Test Ktown Koreadaily parser."""

    def test_detail_k3001(self, fixture_dir):
        """Parse Ktown Koreadaily detail_k3001.html."""
        html_file = fixture_dir / "ktown_koreadaily" / "detail_k3001.html"
        html = html_file.read_text()
        parser = KtownKoreadailyParser()
        result = parser.parse_detail(
            html, "https://ktown.koreadaily.com/ad_rent/rentlist?data=k3001"
        )

        assert result["source_listing_id"] == "k3001"
        assert len(result["content_hash"]) == 64

    def test_detail_k3002(self, fixture_dir):
        """Parse Ktown Koreadaily detail_k3002.html."""
        html_file = fixture_dir / "ktown_koreadaily" / "detail_k3002.html"
        html = html_file.read_text()
        parser = KtownKoreadailyParser()
        result = parser.parse_detail(
            html, "https://ktown.koreadaily.com/ad_rent/rentlist?data=k3002"
        )

        assert result["source_listing_id"] == "k3002"
        assert len(result["content_hash"]) == 64

    def test_detail_k3003(self, fixture_dir):
        """Parse Ktown Koreadaily detail_k3003.html."""
        html_file = fixture_dir / "ktown_koreadaily" / "detail_k3003.html"
        html = html_file.read_text()
        parser = KtownKoreadailyParser()
        result = parser.parse_detail(
            html, "https://ktown.koreadaily.com/ad_rent/rentlist?data=k3003"
        )

        assert result["source_listing_id"] == "k3003"
        assert len(result["content_hash"]) == 64


class TestRadiokoreaParser:
    """Test Radio Korea parser."""

    def test_detail_r4001(self, fixture_dir):
        """Parse Radio Korea detail_r4001.html."""
        html_file = fixture_dir / "radiokorea" / "detail_r4001.html"
        html = html_file.read_text()
        parser = RadiokoreaParser()
        result = parser.parse_detail(html, "https://m.radiokorea.com/c_realestate?wr_id=4001")

        assert result["source_listing_id"] == "4001"
        assert len(result["content_hash"]) == 64

    def test_detail_r4002(self, fixture_dir):
        """Parse Radio Korea detail_r4002.html."""
        html_file = fixture_dir / "radiokorea" / "detail_r4002.html"
        html = html_file.read_text()
        parser = RadiokoreaParser()
        result = parser.parse_detail(html, "https://m.radiokorea.com/c_realestate?wr_id=4002")

        assert result["source_listing_id"] == "4002"
        assert len(result["content_hash"]) == 64

    def test_detail_r4003(self, fixture_dir):
        """Parse Radio Korea detail_r4003.html."""
        html_file = fixture_dir / "radiokorea" / "detail_r4003.html"
        html = html_file.read_text()
        parser = RadiokoreaParser()
        result = parser.parse_detail(html, "https://m.radiokorea.com/c_realestate?wr_id=4003")

        assert result["source_listing_id"] == "4003"
        assert len(result["content_hash"]) == 64


class TestInferLocationWiring:
    """Verify each parser wires the consolidated infer_location chain correctly.

    Two regressions per parser, exercised with synthetic minimal HTML that hits
    each parser's title/body selectors:
      - bracketed-title without a 위치 label -> raw_location combines bracket + first body line
      - labelled 위치/Location line -> labelled value wins over bracket and body head
    """

    # --- svkoreans ---

    def test_svkoreans_infers_location_from_bracket_when_no_label(self):
        html = (
            "<div class='view_wrap'>"
            "<h1>[LA] 다운타운 1베드룸 월세</h1>"
            "<div class='content'>"
            "<p>LA 다운타운 7th Street 콘도 렌트합니다.</p>"
            "<p>월세: $1,500</p>"
            "</div></div>"
        )
        result = SVKoreansParser().parse_detail(html, "https://svkoreans.com/rent_housing/9001")
        # Bracket already in head -> head alone (no double prefix).
        assert result["raw_location"] == "LA 다운타운 7th Street 콘도 렌트합니다."

    def test_svkoreans_labelled_wins_over_bracket_and_head(self):
        html = (
            "<div class='view_wrap'>"
            "<h1>[OC] 풀러턴 콘도</h1>"
            "<div class='content'>"
            "<p>OC 풀러턴 다운타운 콘도 렌트</p>"
            "<p>위치: 어바인 근처 6th Avenue</p>"
            "</div></div>"
        )
        result = SVKoreansParser().parse_detail(html, "https://svkoreans.com/rent_housing/9002")
        assert result["raw_location"] == "어바인 근처 6th Avenue"

    # --- gtksa ---

    def test_gtksa_infers_location_from_bracket_when_no_label(self):
        html = (
            "<div class='view_title'>[애틀랜타] 룸메이트 구합니다</div>"
            "<div class='view_content'>"
            "<p>둘루스 다운타운 콘도</p>"
            "<p>월세: $1,200</p>"
            "</div>"
        )
        result = GTKSAParser().parse_detail(
            html, "https://gtksa.net/bbs/board.php?bo_table=rent&wr_id=9101"
        )
        # Bracket "애틀랜타" not in head -> combine.
        assert result["raw_location"] == "애틀랜타 둘루스 다운타운 콘도"

    def test_gtksa_labelled_wins(self):
        html = (
            "<div class='view_title'>[애틀랜타] 콘도</div>"
            "<div class='view_content'>"
            "<p>둘루스 다운타운 콘도</p>"
            "<p>위치: Atlanta Buford Hwy 123</p>"
            "</div>"
        )
        result = GTKSAParser().parse_detail(
            html, "https://gtksa.net/bbs/board.php?bo_table=rent&wr_id=9102"
        )
        assert result["raw_location"] == "Atlanta Buford Hwy 123"

    # --- ktown_koreadaily ---

    def test_ktown_koreadaily_infers_location_from_bracket_when_no_label(self):
        html = (
            "<div class='rent_detail'>"
            "<h2>[코리아타운] 스튜디오 렌트</h2>"
            "<div class='body'>"
            "<p>할리우드 인근 스튜디오 풀퍼니쳐</p>"
            "<p>월세: $1,800</p>"
            "</div></div>"
        )
        result = KtownKoreadailyParser().parse_detail(
            html, "https://ktown.koreadaily.com/ad_rent/rentlist?data=k9201"
        )
        assert result["raw_location"] == "코리아타운 할리우드 인근 스튜디오 풀퍼니쳐"

    def test_ktown_koreadaily_labelled_wins(self):
        html = (
            "<div class='rent_detail'>"
            "<h2>[코리아타운] 스튜디오</h2>"
            "<div class='body'>"
            "<p>할리우드 인근 스튜디오</p>"
            "<p>Location: 3rd & Vermont, Los Angeles</p>"
            "</div></div>"
        )
        result = KtownKoreadailyParser().parse_detail(
            html, "https://ktown.koreadaily.com/ad_rent/rentlist?data=k9202"
        )
        assert result["raw_location"] == "3rd & Vermont, Los Angeles"

    # --- missyusa ---

    def test_missyusa_infers_location_from_bracket_when_no_label(self):
        html = (
            "<div class='post_detail'>"
            "<h1>[뉴욕] 플러싱 스튜디오 렌트</h1>"
            "<div class='content'>"
            "<p>퀸즈 플러싱 메인스트릿 콘도</p>"
            "<p>월세: $2,000</p>"
            "</div></div>"
        )
        result = MissyusaParser().parse_detail(html, "https://missyusa.com/town9?idx=9301")
        assert result["raw_location"] == "뉴욕 퀸즈 플러싱 메인스트릿 콘도"

    def test_missyusa_labelled_wins(self):
        html = (
            "<div class='post_detail'>"
            "<h1>[뉴욕] 플러싱 스튜디오</h1>"
            "<div class='content'>"
            "<p>퀸즈 플러싱 메인스트릿</p>"
            "<p>위치: 뉴저지 Fort Lee Main Street</p>"
            "</div></div>"
        )
        result = MissyusaParser().parse_detail(html, "https://missyusa.com/town9?idx=9302")
        assert result["raw_location"] == "뉴저지 Fort Lee Main Street"

    # --- radiokorea ---

    def test_radiokorea_infers_location_from_bracket_when_no_label(self):
        html = (
            "<div class='realestate_view'>"
            "<h1>[LA] 한인타운 콘도</h1>"
            "<div class='view_content'>"
            "<p>버뱅크 다운타운 콘도 렌트</p>"
            "<p>월세: $2,200</p>"
            "</div></div>"
        )
        result = RadiokoreaParser().parse_detail(
            html, "https://m.radiokorea.com/c_realestate?wr_id=9401"
        )
        assert result["raw_location"] == "LA 버뱅크 다운타운 콘도 렌트"

    def test_radiokorea_labelled_wins(self):
        html = (
            "<div class='realestate_view'>"
            "<h1>[LA] 한인타운 콘도</h1>"
            "<div class='view_content'>"
            "<p>버뱅크 다운타운 콘도</p>"
            "<p>위치: Wilshire Blvd 3rd Street</p>"
            "</div></div>"
        )
        result = RadiokoreaParser().parse_detail(
            html, "https://m.radiokorea.com/c_realestate?wr_id=9402"
        )
        assert result["raw_location"] == "Wilshire Blvd 3rd Street"

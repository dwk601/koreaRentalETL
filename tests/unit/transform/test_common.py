"""Tests for transform/parsers/_common.py helpers."""

from korean_rental_etl.extract.raw_writer import compute_content_hash as raw_compute_hash
from korean_rental_etl.transform.parsers._common import (
    compute_content_hash,
    extract_body_text,
    extract_labelled_field,
    extract_title_bracket,
    first_body_line,
    infer_location,
)


class TestComputeContentHash:
    """Test content hash standardization."""

    def test_full_64_char_digest(self):
        """Verify compute_content_hash returns full 64-char SHA-256."""
        html = "<html><body>test</body></html>"
        digest = compute_content_hash(html)
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)

    def test_matches_raw_writer(self):
        """Verify transform parser hash matches raw_writer hash."""
        html = "<html><body>Korean rental listing</body></html>"
        assert compute_content_hash(html) == raw_compute_hash(html)


class TestExtractLabelledField:
    """Test labelled field extraction."""

    def test_ascii_colon(self):
        """Extract value after ASCII colon."""
        text = "위치: LA\n월세: $1,500"
        assert extract_labelled_field(text, ["위치"]) == "LA"

    def test_full_width_colon(self):
        """Extract value after full-width colon."""
        text = "위치：LA\n월세：$1,500"
        assert extract_labelled_field(text, ["위치"]) == "LA"

    def test_multi_label_fallback(self):
        """Try multiple labels and return first match."""
        text = "연락처: 213-555-1234\nContact: 949-555-5678"
        # Should match the first label that exists
        result = extract_labelled_field(text, ["연락처", "Contact"])
        assert result == "213-555-1234"

    def test_missing_label(self):
        """Return empty string if label not found."""
        text = "위치: LA\n월세: $1,500"
        assert extract_labelled_field(text, ["보증금"]) == ""

    def test_empty_text(self):
        """Return empty string for empty text."""
        assert extract_labelled_field("", ["위치"]) == ""

    def test_empty_labels(self):
        """Return empty string for empty labels."""
        assert extract_labelled_field("위치: LA", []) == ""

    def test_whitespace_handling(self):
        """Strip whitespace from extracted value."""
        text = "위치:   LA   \n월세: $1,500"
        assert extract_labelled_field(text, ["위치"]) == "LA"


class TestExtractBodyText:
    """Test body text extraction."""

    def test_first_matching_selector(self):
        """Extract text from first matching selector."""
        from bs4 import BeautifulSoup

        html = '<div class="content"><p>Test content</p></div>'
        soup = BeautifulSoup(html, "html.parser")
        result = extract_body_text(soup, [".content", ".body"])
        assert result == "Test content"

    def test_fallback_to_second_selector(self):
        """Fall back to second selector if first doesn't match."""
        from bs4 import BeautifulSoup

        html = '<div class="body"><p>Fallback content</p></div>'
        soup = BeautifulSoup(html, "html.parser")
        result = extract_body_text(soup, [".content", ".body"])
        assert result == "Fallback content"

    def test_preserves_paragraph_breaks(self):
        """Preserve line breaks from multiple paragraphs."""
        from bs4 import BeautifulSoup

        html = '<div class="content"><p>Line 1</p><p>Line 2</p></div>'
        soup = BeautifulSoup(html, "html.parser")
        result = extract_body_text(soup, [".content"])
        assert result == "Line 1\nLine 2"

    def test_no_match(self):
        """Return empty string if no selector matches."""
        from bs4 import BeautifulSoup

        html = '<div class="other"><p>Content</p></div>'
        soup = BeautifulSoup(html, "html.parser")
        result = extract_body_text(soup, [".content", ".body"])
        assert result == ""

    def test_none_soup(self):
        """Return empty string for None soup."""
        result = extract_body_text(None, [".content"])
        assert result == ""

    def test_empty_selectors(self):
        """Return empty string for empty selectors."""
        from bs4 import BeautifulSoup

        html = '<div class="content"><p>Content</p></div>'
        soup = BeautifulSoup(html, "html.parser")
        result = extract_body_text(soup, [])
        assert result == ""


class TestExtractTitleBracket:
    """Test bracket-prefix extraction from titles."""

    def test_simple_ascii_bracket(self):
        assert extract_title_bracket("[LA] 다운타운 1베드") == "LA"

    def test_korean_bracket(self):
        assert extract_title_bracket("[애틀랜타] 룸메이트 구합니다") == "애틀랜타"

    def test_leading_whitespace(self):
        assert extract_title_bracket("   [OC] 풀러턴 콘도 렌트") == "OC"

    def test_inner_whitespace_trimmed(self):
        assert extract_title_bracket("[  뉴욕  ] 스튜디오") == "뉴욕"

    def test_no_bracket(self):
        assert extract_title_bracket("다운타운 1베드룸 월세") == ""

    def test_bracket_not_at_start(self):
        # bracket appearing later in the title is not a prefix tag
        assert extract_title_bracket("월세 $1,500 [LA]") == ""

    def test_empty_input(self):
        assert extract_title_bracket("") == ""


class TestFirstBodyLine:
    """Test first non-empty body line extraction."""

    def test_single_line(self):
        assert first_body_line("맨하탄 미드타운 스튜디오 렌트합니다.") == (
            "맨하탄 미드타운 스튜디오 렌트합니다."
        )

    def test_multi_line_picks_first_non_empty(self):
        body = "OC 풀러턴 다운타운 콘도 렌트\n월세 $2,800\n보증금 $3,000"
        assert first_body_line(body) == "OC 풀러턴 다운타운 콘도 렌트"

    def test_skips_leading_blank_lines(self):
        body = "\n  \n맨하탄 미드타운\n월세 $1,500"
        assert first_body_line(body) == "맨하탄 미드타운"

    def test_strips_leading_whitespace(self):
        assert first_body_line("   LA 다운타운 7th Street") == "LA 다운타운 7th Street"

    def test_empty_input(self):
        assert first_body_line("") == ""

    def test_only_whitespace(self):
        assert first_body_line("   \n\n  ") == ""


class TestInferLocation:
    """Test the consolidated location fallback chain."""

    def test_labelled_wins(self):
        # Labelled value beats bracket and body head.
        assert (
            infer_location(
                "[LA] foo", "맨하탄 미드타운 스튜디오 렌트.", labelled="LA 다운타운 7th Street"
            )
            == "LA 다운타운 7th Street"
        )

    def test_bracket_combined_with_body_head(self):
        # Bracket not in head -> combine.
        result = infer_location("[LA] 다운타운 1베드", "맨하탄 미드타운 스튜디오 렌트.", "")
        assert result == "LA 맨하탄 미드타운 스튜디오 렌트."

    def test_bracket_already_in_head_returns_head_only(self):
        # Bracket appears in head -> head alone is richer.
        result = infer_location("[LA] 다운타운", "LA 다운타운 7th Street 콘도 렌트", "")
        assert result == "LA 다운타운 7th Street 콘도 렌트"

    def test_head_only_when_no_bracket(self):
        result = infer_location("다운타운 1베드룸 월세", "맨하탄 미드타운 스튜디오 렌트.", "")
        assert result == "맨하탄 미드타운 스튜디오 렌트."

    def test_bracket_only_when_no_body(self):
        assert infer_location("[애틀랜타] 룸메이트", "", "") == "애틀랜타"

    def test_all_empty_returns_empty_string(self):
        assert infer_location("", "", "") == ""

    def test_default_labelled_argument(self):
        # labelled defaults to "" - exercise both branches via default.
        assert infer_location("[OC] 풀러턴 콘도", "OC 풀러턴 다운타운") == "OC 풀러턴 다운타운"

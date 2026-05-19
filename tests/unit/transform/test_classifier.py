"""Unit tests for classifier."""

import pytest

from korean_rental_etl.transform.classifier import classify


class TestClassifier:
    """Test category classifier."""

    @pytest.mark.parametrize(
        "title_ko,body_ko,title_en,body_en,expected",
        [
            # Apartment
            ("아파트 2룸", "강남역 근처", "", "", "apartment"),
            ("", "", "Apartment for rent", "2 bedroom", "apartment"),
            ("아파 매매", "", "", "", "apartment"),
            # House
            ("주택 판매", "", "", "", "house"),
            ("", "", "Single family home", "", "house"),
            ("단독주택", "", "", "", "house"),
            # Condo
            ("콘도 렌트", "", "", "", "condo"),
            ("", "", "Condominium", "", "condo"),
            # Room share
            ("룸셰어 구함", "", "", "", "room_share"),
            ("", "", "Room share available", "", "room_share"),
            ("방 나눔", "", "", "", "room_share"),
            # Sublet
            ("전대 가능", "", "", "", "sublet"),
            ("", "", "Sublet available", "", "sublet"),
            # Roommate wanted
            ("룸메이트 찾습니다", "", "", "", "roommate_wanted"),
            ("", "", "Looking for roommate", "", "roommate_wanted"),
            # Commercial
            ("상가 임차", "", "", "", "commercial_space"),
            ("", "", "Commercial office space", "", "commercial_space"),
            ("사무실 렌트", "", "", "", "commercial_space"),
            # Parking
            ("주차장 판매", "", "", "", "parking"),
            ("", "", "Parking garage", "", "parking"),
            # Unmatched -> other
            ("", "", "", "", "other"),
            ("기타 물건", "", "", "", "other"),
            # Priority: apartment > house (both present)
            ("아파트 주택", "", "", "", "apartment"),
            # Mixed KO/EN
            ("아파트 apartment", "", "", "", "apartment"),
        ],
    )
    def test_classify_all_categories(self, title_ko, body_ko, title_en, body_en, expected):
        """Test classification for all 9 categories."""
        result = classify(title_ko, body_ko, title_en, body_en)
        assert result == expected

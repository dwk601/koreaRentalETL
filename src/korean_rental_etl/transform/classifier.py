"""Category classifier (rule-based KO+EN keywords)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Bilingual keyword dictionary for all 9 categories
CATEGORY_KEYWORDS = {
    "apartment": {
        "ko": ["아파트", "아파"],
        "en": ["apartment", "apt"],
    },
    "condo": {
        "ko": ["콘도", "콘도미니엄"],
        "en": ["condo", "condominium"],
    },
    "house": {
        "ko": ["주택", "집", "단독주택"],
        "en": ["house", "home", "single family"],
    },
    "room_share": {
        "ko": ["룸셰어", "방 나눔", "셰어하우스"],
        "en": ["room share", "shared room"],
    },
    "roommate_wanted": {
        "ko": ["룸메이트", "방 구함", "함께 살"],
        "en": ["roommate wanted", "looking for roommate"],
    },
    "sublet": {
        "ko": ["전대", "재임차", "서브렛"],
        "en": ["sublet", "sublease"],
    },
    "commercial_space": {
        "ko": ["상가", "사무실", "점포"],
        "en": ["commercial", "office", "storefront"],
    },
    "parking": {
        "ko": ["주차", "주차장"],
        "en": ["parking", "garage"],
    },
    "other": {
        "ko": [],
        "en": [],
    },
}

# Priority order for multi-match
CATEGORY_PRIORITY = [
    "apartment",
    "condo",
    "house",
    "commercial_space",
    "parking",
    "sublet",
    "room_share",
    "roommate_wanted",
    "other",
]


def classify(title_ko: str = "", body_ko: str = "", title_en: str = "", body_en: str = "") -> str:
    """Classify listing into one of 9 categories.

    Args:
        title_ko: Korean title.
        body_ko: Korean body.
        title_en: English title.
        body_en: English body.

    Returns:
        Category string.
    """
    combined_text = f"{title_ko} {body_ko} {title_en} {body_en}".lower()

    matched_categories = []
    for category in CATEGORY_PRIORITY:
        keywords = CATEGORY_KEYWORDS[category]
        for kw in keywords["ko"] + keywords["en"]:
            if kw.lower() in combined_text:
                matched_categories.append(category)
                break

    if matched_categories:
        return matched_categories[0]  # Return highest priority match

    return "other"

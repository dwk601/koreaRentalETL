"""Shared text parsing utilities for extract and transform layers."""

import re


def extract_title_bracket(title: str) -> str:
    """Extract the leading [bracket] tag from a title.

    Korean rental boards conventionally prefix titles with a city/region tag like
    '[LA] 다운타운 1베드룸 월세 $1,500' or '[애틀랜타] 룸메이트 구합니다'.

    Args:
        title: Title string.

    Returns:
        The bracket contents (e.g. 'LA', '애틀랜타'), or '' if no bracket prefix.
    """
    if not title:
        return ""
    match = re.match(r"\s*\[\s*([^\]]+?)\s*\]", title)
    return match.group(1).strip() if match else ""


def first_body_line(body: str) -> str:
    """Return the first non-empty line of a body block.

    Many Korean rental listings put a free-form location/summary on the first body
    line (e.g. '맨하탄 미드타운 스튜디오 렌트합니다.', 'OC 풀러턴 다운타운 콘도 렌트').

    Args:
        body: Body text.

    Returns:
        First non-empty stripped line, or '' if body is empty.
    """
    if not body:
        return ""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""

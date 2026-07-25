"""Lesson type helpers: principle / code / lab."""

from __future__ import annotations

import re

LESSON_TYPES = ("principle", "code", "lab")
LESSON_TYPE_LABELS = {
    "principle": "原理",
    "code": "代码",
    "lab": "实操",
}


def normalize_lesson_type(value: str | None, *, default: str = "principle") -> str:
    """Return a valid lesson_type or default."""
    if value is None:
        return default
    cleaned = value.strip().lower()
    aliases = {
        "原理": "principle",
        "概念": "principle",
        "intro": "principle",
        "代码": "code",
        "coding": "code",
        "实操": "lab",
        "实验": "lab",
        "动手": "lab",
        "practice": "lab",
        "hands-on": "lab",
        "handson": "lab",
    }
    if cleaned in aliases:
        return aliases[cleaned]
    if cleaned in LESSON_TYPES:
        return cleaned
    return default


def infer_lesson_type(title_anchor: str) -> tuple[str, str]:
    """Heuristic lesson_type from title/filename stem.

    Returns ``(lesson_type, source)`` where source is ``inferred``.
    """
    text = title_anchor.strip().lower()
    # lab / hands-on first
    if re.search(
        r"(实操|实验|动手|练习|跟做|workshop|lab|hands?-?on)",
        text,
        flags=re.IGNORECASE,
    ):
        return "lab", "inferred"
    if re.search(
        r"(代码|实现|coding|ide|源码|api|demo)",
        text,
        flags=re.IGNORECASE,
    ):
        return "code", "inferred"
    if re.search(
        r"(原理|概念|简介|介绍|理解|理论|qkv|注意力)",
        text,
        flags=re.IGNORECASE,
    ):
        return "principle", "inferred"
    return "principle", "inferred"

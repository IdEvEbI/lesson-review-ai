"""Lesson type helpers: principle / code / lab."""

from __future__ import annotations

import re

LESSON_TYPES = ("principle", "code", "lab")
LESSON_TYPE_LABELS = {
    "principle": "原理",
    "code": "代码",
    "lab": "实操",
}

# Priority: lab hands-on → install/config → code → principle → default principle
_LAB_HANDS_ON = re.compile(
    r"(实操|实验|动手|练习|跟做|workshop|lab|hands?-?on)",
    re.IGNORECASE,
)
_LAB_INSTALL = re.compile(
    r"(安装|配置|环境|部署|搭环境)",
    re.IGNORECASE,
)
_CODE = re.compile(
    r"(代码|实现|coding|ide|源码|api|demo)",
    re.IGNORECASE,
)
_PRINCIPLE = re.compile(
    r"(原理|概念|简介|介绍|理解|理论|qkv|注意力)",
    re.IGNORECASE,
)

_ALIASES = {
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
    "安装": "lab",
    "配置": "lab",
}


class LessonTypeError(ValueError):
    """Invalid lesson_type value (e.g. CLI typo)."""


def normalize_lesson_type(value: str | None, *, default: str = "principle") -> str:
    """Return a valid lesson_type or default (lenient; for inference fallbacks)."""
    if value is None:
        return default
    cleaned = value.strip().lower()
    if cleaned in _ALIASES:
        return _ALIASES[cleaned]
    if cleaned in LESSON_TYPES:
        return cleaned
    return default


def parse_lesson_type_cli(value: str) -> str:
    """Parse ``--lesson-type``; reject typos instead of silently defaulting.

    Raises:
        LessonTypeError: when value is not principle|code|lab (or known alias).
    """
    cleaned = value.strip().lower()
    if cleaned in _ALIASES:
        return _ALIASES[cleaned]
    if cleaned in LESSON_TYPES:
        return cleaned
    allowed = "|".join(LESSON_TYPES)
    raise LessonTypeError(
        f"invalid --lesson-type {value!r}; expected {allowed} "
        f"(aliases: 原理/代码/实操). Did you mean 'lab'?"
    )


def infer_lesson_type(title_anchor: str) -> tuple[str, str]:
    """Heuristic lesson_type from title/filename stem.

    Returns ``(lesson_type, source)`` where source is ``inferred``.
    Lab / install signals beat principle when both match (report contract §10.1).
    """
    text = title_anchor.strip().lower()
    if _LAB_HANDS_ON.search(text) or _LAB_INSTALL.search(text):
        return "lab", "inferred"
    if _CODE.search(text):
        return "code", "inferred"
    if _PRINCIPLE.search(text):
        return "principle", "inferred"
    return "principle", "inferred"

"""Normalize LLM markdown outputs before writing artifacts."""

from __future__ import annotations

import re

_META_MARKERS = (
    "以下是",
    "以下为",
    "完整 Pass",
    "Pass B",
    "根据系统",
    "已收到",
    "按顺序包含",
    "系统指令",
)


def strip_markdown_fence(text: str) -> str:
    """Unwrap a whole-document ```markdown ... ``` fence if present."""
    cleaned = text.strip()
    if not cleaned:
        return cleaned

    whole = re.fullmatch(
        r"```(?:markdown|md)?\s*\n([\s\S]*?)\n```",
        cleaned,
        flags=re.IGNORECASE,
    )
    if whole:
        return whole.group(1).strip()

    # Preamble + fenced body (common model habit)
    fenced = re.search(
        r"```(?:markdown|md)?\s*\n([\s\S]*?)\n```",
        cleaned,
        flags=re.IGNORECASE,
    )
    if not fenced:
        return cleaned

    before = cleaned[: fenced.start()].strip()
    if not before:
        return fenced.group(1).strip()
    if len(before) < 500 and (
        any(marker in before for marker in _META_MARKERS) or before.startswith("好")
    ):
        return fenced.group(1).strip()
    return cleaned


def strip_leading_meta_before_heading(text: str) -> str:
    """Drop short chatty preamble before the first Markdown heading."""
    cleaned = text.strip()
    if not cleaned:
        return cleaned
    match = re.search(r"(?m)^#{1,3}\s+\S", cleaned)
    if not match or match.start() == 0:
        return cleaned
    before = cleaned[: match.start()].strip()
    if len(before) < 500 and any(marker in before for marker in _META_MARKERS):
        return cleaned[match.start() :].strip()
    if len(before) < 200 and before.startswith("好"):
        return cleaned[match.start() :].strip()
    return cleaned


def normalize_llm_markdown(text: str) -> str:
    """Strip fences and leading meta so artifacts are plain Markdown."""
    return strip_leading_meta_before_heading(strip_markdown_fence(text))

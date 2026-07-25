"""Helpers for corrected transcript text used by Pass A / Pass B."""

from __future__ import annotations

_PREAMBLE_MARKERS = ("纠错", "补全标点", "补标点", "转写进行", "纠正后的结果", "纠错后的结果")


def strip_correction_preamble(text: str) -> str:
    """Remove common LLM correction meta-preambles before analysis.

    Keeps the classroom transcript body when the model prefixes a short
    explanation (optionally followed by a horizontal rule).
    """
    cleaned = text.strip()
    if not cleaned:
        return cleaned

    # Preamble + --- separator within the first ~500 chars
    if "---" in cleaned[:500]:
        first, rest = cleaned.split("---", 1)
        if len(first) < 400 and any(marker in first for marker in _PREAMBLE_MARKERS):
            return rest.lstrip("\n").strip()

    lines = cleaned.splitlines()
    first_line = lines[0].strip() if lines else ""
    if first_line and len(first_line) < 160 and any(
        marker in first_line for marker in _PREAMBLE_MARKERS
    ):
        index = 1
        while index < len(lines) and not lines[index].strip():
            index += 1
        if index < len(lines) and lines[index].strip() == "---":
            index += 1
            while index < len(lines) and not lines[index].strip():
                index += 1
        if index < len(lines) and index > 0:
            return "\n".join(lines[index:]).strip()

    return cleaned

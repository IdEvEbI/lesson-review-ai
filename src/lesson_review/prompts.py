"""Load versioned prompt markdown from the repository ``prompts/`` directory."""

from __future__ import annotations

from pathlib import Path

from lesson_review.config import REPO_ROOT

PROMPTS_DIR = REPO_ROOT / "prompts"

PROMPT_FILES = {
    "system_tone": "system_tone.md",
    "asr_correct": "asr_correct.md",
    "knowledge_cases": "knowledge_cases.md",
    "structure_single": "structure_single.md",
    "structure_module": "structure_module.md",
    "teaching_outline": "teaching_outline.md",
    "coach_feedback": "coach_feedback.md",
    "conduct_scan": "conduct_scan.md",
    "pedagogy_type": "pedagogy_type.md",
    "batch_outline": "batch_outline.md",
}


class PromptError(Exception):
    """Raised when a prompt file cannot be loaded."""


def load_prompt(name: str) -> str:
    """Return prompt markdown text for a logical name (e.g. ``asr_correct``)."""
    filename = PROMPT_FILES.get(name)
    if filename is None:
        raise PromptError(f"unknown prompt name: {name!r}")
    path = PROMPTS_DIR / filename
    if not path.is_file():
        raise PromptError(f"prompt file missing: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise PromptError(f"prompt file empty: {path}")
    return text


def combine_system_prompts(*names: str) -> str:
    """Concatenate multiple prompt files with blank-line separators."""
    parts = [load_prompt(name) for name in names]
    return "\n\n".join(parts)

"""Load environment defaults for the CLI."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Repo root: src/lesson_review/../../
REPO_ROOT = Path(__file__).resolve().parents[2]


def load_env() -> None:
    """Load `.env` from the repository root if present."""
    load_dotenv(REPO_ROOT / ".env")


def getenv(name: str, default: str | None = None) -> str | None:
    load_env()
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value

"""Dependency and input checks for dry-run and preflight."""

from __future__ import annotations

import importlib.util
import shutil
from dataclasses import dataclass
from pathlib import Path

from lesson_review.config import getenv

# Exit codes from docs/01-product/002_cli-contract
EXIT_OK = 0
EXIT_USER = 1
EXIT_DEPS = 2
EXIT_PIPELINE = 3

VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov", ".avi", ".webm"}
AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".flac", ".aac", ".ogg"}
SUPPORTED_SUFFIXES = VIDEO_SUFFIXES | AUDIO_SUFFIXES


@dataclass(frozen=True)
class CheckItem:
    name: str
    ok: bool
    detail: str
    required: bool = True


def check_ffmpeg() -> CheckItem:
    path = shutil.which("ffmpeg")
    if path:
        return CheckItem("ffmpeg", True, path)
    return CheckItem("ffmpeg", False, "not found on PATH (brew install ffmpeg)")


def check_mlx_whisper() -> CheckItem:
    if importlib.util.find_spec("mlx_whisper") is not None:
        return CheckItem("mlx-whisper", True, "importable")
    return CheckItem(
        "mlx-whisper",
        False,
        "not installed (will be added in ASR slice)",
        required=False,
    )


def check_llm_api_key() -> CheckItem:
    key = getenv("LLM_API_KEY")
    if key:
        return CheckItem("LLM_API_KEY", True, "set in environment / .env")
    return CheckItem(
        "LLM_API_KEY",
        False,
        "missing (copy .env.example → .env)",
        required=False,
    )


def check_input_path(path: Path) -> CheckItem:
    if not path.exists():
        return CheckItem("input", False, f"path does not exist: {path}")
    if not path.is_file():
        return CheckItem("input", False, f"not a file: {path}")
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        return CheckItem(
            "input",
            False,
            f"unsupported suffix {suffix!r}; expected one of {sorted(SUPPORTED_SUFFIXES)}",
        )
    kind = "video" if suffix in VIDEO_SUFFIXES else "audio"
    return CheckItem("input", True, f"{kind}: {path.resolve()}")


def run_dependency_checks() -> list[CheckItem]:
    return [check_ffmpeg(), check_mlx_whisper(), check_llm_api_key()]

"""ASR helpers: local mlx-whisper transcription."""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path
from typing import Any

from lesson_review.checks import (
    AUDIO_SUFFIXES,
    EXIT_DEPS,
    EXIT_PIPELINE,
    EXIT_USER,
    check_input_path,
)
from lesson_review.config import getenv

DEFAULT_WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"
DEFAULT_WHISPER_LANGUAGE = "zh"


class TranscribeError(Exception):
    """Raised when transcription cannot complete."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def default_transcript_output_path(
    input_path: Path,
    output_root: Path = Path("output"),
) -> Path:
    """Return ``output/<stem>/transcript_raw.json``."""
    return output_root / input_path.stem / "transcript_raw.json"


def resolve_whisper_model(cli_model: str | None = None) -> str:
    if cli_model:
        return cli_model
    return getenv("WHISPER_MODEL", DEFAULT_WHISPER_MODEL) or DEFAULT_WHISPER_MODEL


def resolve_whisper_language(cli_language: str | None = None) -> str:
    if cli_language:
        return cli_language
    return (
        getenv("WHISPER_LANGUAGE", DEFAULT_WHISPER_LANGUAGE) or DEFAULT_WHISPER_LANGUAGE
    )


def normalize_transcript(
    raw: dict[str, Any],
    *,
    source: Path,
    model: str,
    language: str,
) -> dict[str, Any]:
    """Normalize mlx-whisper result into a stable transcript_raw schema."""
    segments_out: list[dict[str, Any]] = []
    for index, segment in enumerate(raw.get("segments") or []):
        segments_out.append(
            {
                "id": int(segment.get("id", index)),
                "start": float(segment.get("start", 0.0)),
                "end": float(segment.get("end", 0.0)),
                "text": str(segment.get("text", "")).strip(),
            }
        )

    text = str(raw.get("text", "")).strip()
    if not text and segments_out:
        text = " ".join(s["text"] for s in segments_out if s["text"]).strip()

    return {
        "engine": "mlx_whisper",
        "model": model,
        "language": language,
        "source": str(source.resolve()),
        "text": text,
        "segments": segments_out,
    }


def write_transcript_json(payload: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path.resolve()


def _require_audio_input(path: Path) -> None:
    check = check_input_path(path)
    if not check.ok:
        raise TranscribeError(check.detail, EXIT_USER)
    if path.suffix.lower() not in AUDIO_SUFFIXES:
        raise TranscribeError(
            f"transcribe expects an audio file; got {path.suffix.lower()!r}. "
            "Run extract-audio first for video inputs.",
            EXIT_USER,
        )


def _require_deps() -> None:
    if shutil.which("ffmpeg") is None:
        raise TranscribeError(
            "ffmpeg not found on PATH (brew install ffmpeg)",
            EXIT_DEPS,
        )
    if importlib.util.find_spec("mlx_whisper") is None:
        raise TranscribeError(
            "mlx-whisper not installed (uv sync)",
            EXIT_DEPS,
        )


def run_mlx_transcribe(
    audio_path: Path,
    *,
    model: str,
    language: str,
) -> dict[str, Any]:
    """Call mlx_whisper.transcribe (separated for easy mocking)."""
    import mlx_whisper

    return mlx_whisper.transcribe(
        str(audio_path),
        path_or_hf_repo=model,
        language=language,
        verbose=False,
    )


def transcribe_audio(
    input_path: Path,
    output_path: Path | None = None,
    *,
    language: str | None = None,
    whisper_model: str | None = None,
    output_root: Path = Path("output"),
) -> Path:
    """Transcribe audio to transcript_raw.json. Returns the written path."""
    _require_audio_input(input_path)
    _require_deps()

    model = resolve_whisper_model(whisper_model)
    lang = resolve_whisper_language(language)
    dest = output_path or default_transcript_output_path(input_path, output_root)

    try:
        raw = run_mlx_transcribe(input_path, model=model, language=lang)
    except TranscribeError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface any ASR failure as exit 3
        raise TranscribeError(f"mlx-whisper failed: {exc}", EXIT_PIPELINE) from exc

    if not isinstance(raw, dict):
        raise TranscribeError(
            f"unexpected mlx-whisper result type: {type(raw).__name__}",
            EXIT_PIPELINE,
        )

    payload = normalize_transcript(
        raw,
        source=input_path,
        model=model,
        language=lang,
    )
    return write_transcript_json(payload, dest)

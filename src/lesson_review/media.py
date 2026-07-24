"""Media helpers: ffmpeg audio extraction."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from lesson_review.checks import (
    EXIT_DEPS,
    EXIT_PIPELINE,
    EXIT_USER,
    VIDEO_SUFFIXES,
    check_input_path,
)

SUPPORTED_AUDIO_FORMATS = ("mp3", "wav")
DEFAULT_AUDIO_FORMAT = "mp3"
DEFAULT_MP3_BITRATE = "96k"
DEFAULT_WAV_SAMPLE_RATE = 16000


class ExtractAudioError(Exception):
    """Raised when extract-audio cannot complete."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def default_audio_output_path(
    input_path: Path,
    fmt: str,
    output_root: Path = Path("output"),
) -> Path:
    """Return ``output/<stem>/audio/<stem>.<fmt>``."""
    stem = input_path.stem
    return output_root / stem / "audio" / f"{stem}.{fmt}"


def build_ffmpeg_cmd(input_path: Path, output_path: Path, fmt: str) -> list[str]:
    """Build ffmpeg argv for mono audio extraction."""
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        "1",
    ]
    if fmt == "mp3":
        cmd.extend(
            [
                "-ar",
                str(DEFAULT_WAV_SAMPLE_RATE),
                "-b:a",
                DEFAULT_MP3_BITRATE,
                str(output_path),
            ]
        )
    elif fmt == "wav":
        cmd.extend(
            [
                "-ar",
                str(DEFAULT_WAV_SAMPLE_RATE),
                "-acodec",
                "pcm_s16le",
                str(output_path),
            ]
        )
    else:
        raise ExtractAudioError(
            f"unsupported format {fmt!r}; expected one of {SUPPORTED_AUDIO_FORMATS}",
            EXIT_USER,
        )
    return cmd


def extract_audio(
    input_path: Path,
    output_path: Path | None = None,
    fmt: str = DEFAULT_AUDIO_FORMAT,
    *,
    output_root: Path = Path("output"),
) -> Path:
    """Extract mono audio from a video (or re-encode audio) via ffmpeg.

    Returns the written audio path.
    """
    fmt = fmt.lower().lstrip(".")
    if fmt not in SUPPORTED_AUDIO_FORMATS:
        raise ExtractAudioError(
            f"unsupported format {fmt!r}; expected one of {SUPPORTED_AUDIO_FORMATS}",
            EXIT_USER,
        )

    input_check = check_input_path(input_path)
    if not input_check.ok:
        raise ExtractAudioError(input_check.detail, EXIT_USER)

    if input_path.suffix.lower() not in VIDEO_SUFFIXES:
        # Allow audio inputs as normalize path; still require a known media suffix.
        pass

    if shutil.which("ffmpeg") is None:
        raise ExtractAudioError(
            "ffmpeg not found on PATH (brew install ffmpeg)",
            EXIT_DEPS,
        )

    dest = output_path or default_audio_output_path(input_path, fmt, output_root)
    if dest.suffix.lower() != f".{fmt}":
        raise ExtractAudioError(
            f"output suffix {dest.suffix!r} does not match --format {fmt!r}",
            EXIT_USER,
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_ffmpeg_cmd(input_path, dest, fmt)

    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise ExtractAudioError(f"failed to launch ffmpeg: {exc}", EXIT_PIPELINE) from exc

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        if not detail:
            detail = f"ffmpeg exited with code {completed.returncode}"
        raise ExtractAudioError(detail, EXIT_PIPELINE)

    if not dest.is_file() or dest.stat().st_size == 0:
        raise ExtractAudioError(
            f"ffmpeg reported success but output missing or empty: {dest}",
            EXIT_PIPELINE,
        )

    return dest.resolve()

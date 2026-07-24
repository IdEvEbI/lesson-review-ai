"""Unit tests for mlx-whisper transcription (mocked)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from lesson_review.asr import (
    default_transcript_output_path,
    normalize_transcript,
    transcribe_audio,
)
from lesson_review.checks import EXIT_DEPS, EXIT_PIPELINE, EXIT_USER
from lesson_review.cli import app

runner = CliRunner()


def test_default_transcript_output_path() -> None:
    path = default_transcript_output_path(Path("output/02.demo/audio/02.demo.mp3"))
    assert path == Path("output/02.demo/transcript_raw.json")


def test_normalize_transcript() -> None:
    raw = {
        "text": " 你好世界 ",
        "segments": [
            {"id": 0, "start": 0.0, "end": 1.2, "text": " 你好"},
            {"start": 1.2, "end": 2.0, "text": "世界 "},
        ],
    }
    payload = normalize_transcript(
        raw,
        source=Path("/tmp/a.mp3"),
        model="mlx-community/whisper-large-v3-turbo",
        language="zh",
    )
    assert payload["engine"] == "mlx_whisper"
    assert payload["text"] == "你好世界"
    assert payload["segments"][0]["text"] == "你好"
    assert payload["segments"][1]["id"] == 1
    assert payload["segments"][1]["end"] == 2.0


def test_transcribe_rejects_video(tmp_path: Path) -> None:
    video = tmp_path / "clip.avi"
    video.write_bytes(b"fake")
    with pytest.raises(Exception) as exc_info:
        transcribe_audio(video)
    assert exc_info.value.exit_code == EXIT_USER


def test_transcribe_missing_mlx(tmp_path: Path) -> None:
    audio = tmp_path / "clip.mp3"
    audio.write_bytes(b"fake")
    with (
        patch("lesson_review.asr.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("lesson_review.asr.importlib.util.find_spec", return_value=None),
    ):
        with pytest.raises(Exception) as exc_info:
            transcribe_audio(audio)
    assert exc_info.value.exit_code == EXIT_DEPS


def test_transcribe_success_mocked(tmp_path: Path) -> None:
    audio = tmp_path / "clip.mp3"
    audio.write_bytes(b"fake-audio")
    out = tmp_path / "transcript_raw.json"

    fake_raw = {
        "text": "注意力机制",
        "segments": [{"id": 0, "start": 0.0, "end": 1.5, "text": "注意力机制"}],
    }

    with (
        patch("lesson_review.asr.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("lesson_review.asr.importlib.util.find_spec", return_value=object()),
        patch("lesson_review.asr.run_mlx_transcribe", return_value=fake_raw) as run_mock,
    ):
        dest = transcribe_audio(audio, out, language="zh", whisper_model="tiny-test")

    assert dest == out.resolve()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["text"] == "注意力机制"
    assert payload["model"] == "tiny-test"
    assert payload["segments"][0]["start"] == 0.0
    run_mock.assert_called_once()


def test_transcribe_asr_failure(tmp_path: Path) -> None:
    audio = tmp_path / "clip.mp3"
    audio.write_bytes(b"fake")
    with (
        patch("lesson_review.asr.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("lesson_review.asr.importlib.util.find_spec", return_value=object()),
        patch(
            "lesson_review.asr.run_mlx_transcribe",
            side_effect=RuntimeError("boom"),
        ),
    ):
        with pytest.raises(Exception) as exc_info:
            transcribe_audio(audio)
    assert exc_info.value.exit_code == EXIT_PIPELINE


def test_cli_transcribe_success(tmp_path: Path) -> None:
    audio = tmp_path / "lesson.mp3"
    audio.write_bytes(b"fake")
    out = tmp_path / "out.json"
    fake_raw = {
        "text": "ok",
        "segments": [{"id": 0, "start": 0.0, "end": 0.5, "text": "ok"}],
    }
    with (
        patch("lesson_review.asr.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("lesson_review.asr.importlib.util.find_spec", return_value=object()),
        patch("lesson_review.asr.run_mlx_transcribe", return_value=fake_raw),
    ):
        result = runner.invoke(
            app,
            ["transcribe", str(audio), "-o", str(out)],
        )
    assert result.exit_code == 0
    assert str(out.resolve()) in result.stdout

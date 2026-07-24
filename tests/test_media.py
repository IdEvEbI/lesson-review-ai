"""Unit tests for ffmpeg audio extraction (mocked subprocess)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from lesson_review.checks import EXIT_DEPS, EXIT_PIPELINE, EXIT_USER
from lesson_review.cli import app
from lesson_review.media import (
    build_ffmpeg_cmd,
    default_audio_output_path,
    extract_audio,
)

runner = CliRunner()


def test_default_audio_output_path() -> None:
    path = default_audio_output_path(Path("data/input/02.demo.avi"), "mp3")
    assert path == Path("output/02.demo/audio/02.demo.mp3")


def test_build_ffmpeg_cmd_mp3() -> None:
    cmd = build_ffmpeg_cmd(Path("in.avi"), Path("out.mp3"), "mp3")
    assert cmd[0] == "ffmpeg"
    assert "-vn" in cmd
    assert "-ac" in cmd and "1" in cmd
    assert "-ar" in cmd and "16000" in cmd
    assert "-b:a" in cmd and "96k" in cmd
    assert cmd[-1] == "out.mp3"


def test_build_ffmpeg_cmd_wav() -> None:
    cmd = build_ffmpeg_cmd(Path("in.avi"), Path("out.wav"), "wav")
    assert "-ar" in cmd and "16000" in cmd
    assert "pcm_s16le" in cmd
    assert cmd[-1] == "out.wav"


def test_extract_audio_missing_input(tmp_path: Path) -> None:
    with pytest.raises(Exception) as exc_info:
        extract_audio(tmp_path / "missing.avi")
    assert exc_info.value.exit_code == EXIT_USER


def test_extract_audio_unsupported_format(tmp_path: Path) -> None:
    video = tmp_path / "clip.avi"
    video.write_bytes(b"fake")
    with pytest.raises(Exception) as exc_info:
        extract_audio(video, fmt="flac")
    assert exc_info.value.exit_code == EXIT_USER


def test_extract_audio_missing_ffmpeg(tmp_path: Path) -> None:
    video = tmp_path / "clip.avi"
    video.write_bytes(b"fake")
    with patch("lesson_review.media.shutil.which", return_value=None):
        with pytest.raises(Exception) as exc_info:
            extract_audio(video)
    assert exc_info.value.exit_code == EXIT_DEPS


def test_extract_audio_success_mocked(tmp_path: Path) -> None:
    video = tmp_path / "clip.avi"
    video.write_bytes(b"fake-video")
    out = tmp_path / "clip.mp3"

    def fake_run(cmd, check, capture_output, text):  # noqa: ANN001
        Path(cmd[-1]).write_bytes(b"id3-fake-audio")
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        result.stdout = ""
        return result

    with (
        patch("lesson_review.media.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("lesson_review.media.subprocess.run", side_effect=fake_run) as run_mock,
    ):
        dest = extract_audio(video, out, fmt="mp3")

    assert dest == out.resolve()
    assert out.is_file()
    run_mock.assert_called_once()
    called_cmd = run_mock.call_args.args[0]
    assert called_cmd[0] == "ffmpeg"
    assert str(video) in called_cmd
    assert str(out) in called_cmd


def test_extract_audio_ffmpeg_failure(tmp_path: Path) -> None:
    video = tmp_path / "clip.avi"
    video.write_bytes(b"fake")
    out = tmp_path / "clip.mp3"

    failed = MagicMock()
    failed.returncode = 1
    failed.stderr = "Invalid data found"
    failed.stdout = ""

    with (
        patch("lesson_review.media.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("lesson_review.media.subprocess.run", return_value=failed),
    ):
        with pytest.raises(Exception) as exc_info:
            extract_audio(video, out)
    assert exc_info.value.exit_code == EXIT_PIPELINE
    assert "Invalid data" in str(exc_info.value)


def test_cli_extract_audio_success(tmp_path: Path) -> None:
    video = tmp_path / "lesson.avi"
    video.write_bytes(b"fake")
    out = tmp_path / "lesson.mp3"

    def fake_run(cmd, check, capture_output, text):  # noqa: ANN001
        Path(cmd[-1]).write_bytes(b"audio")
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        result.stdout = ""
        return result

    with (
        patch("lesson_review.media.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("lesson_review.media.subprocess.run", side_effect=fake_run),
    ):
        result = runner.invoke(
            app,
            ["extract-audio", str(video), "-o", str(out), "--format", "mp3"],
        )

    assert result.exit_code == 0
    assert str(out.resolve()) in result.stdout


def test_cli_extract_audio_user_error(tmp_path: Path) -> None:
    result = runner.invoke(app, ["extract-audio", str(tmp_path / "nope.avi")])
    assert result.exit_code == EXIT_USER

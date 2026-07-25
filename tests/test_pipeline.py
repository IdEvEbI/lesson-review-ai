"""Tests for single-video pipeline and report rendering (mocked)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from lesson_review.checks import EXIT_DEPS, EXIT_OK
from lesson_review.cli import app
from lesson_review.pipeline import run_single
from lesson_review.report import render_single_report

runner = CliRunner()


def test_render_single_report_contains_contract_sections() -> None:
    text = render_single_report(
        run_id="20260725-120000_abcd1234",
        input_path=Path("sample.mp4"),
        structure_md="## 课程结构与要点\n\n- 开场总：示例",
        coach_md="## 结论摘要\n\n可读。\n\n## 提升建议\n\n### 合格线（必须改）\n",
        corrected_relpath="transcript_corrected.md",
    )
    assert "# 课评报告 · 单视频" in text
    assert "## 元信息" in text
    assert "## 附录" in text
    assert "transcript_corrected.md" in text
    assert "20260725-120000_abcd1234" in text


def test_run_single_skip_llm_mocked(tmp_path: Path) -> None:
    video = tmp_path / "lesson.mp4"
    video.write_bytes(b"fake-video")

    def fake_extract(input_path, output_path, fmt="mp3", output_root=None):  # noqa: ANN001
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"audio")
        return output_path.resolve()

    def fake_transcribe(input_path, output_path, **kwargs):  # noqa: ANN001
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps({"text": "你好", "segments": []}, ensure_ascii=False),
            encoding="utf-8",
        )
        return output_path.resolve()

    with (
        patch("lesson_review.pipeline.extract_audio", side_effect=fake_extract),
        patch("lesson_review.pipeline.transcribe_audio", side_effect=fake_transcribe),
    ):
        result = run_single(
            video,
            output_dir=tmp_path / "out",
            skip_llm=True,
            force=True,
        )

    assert result.report_path is None
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["mode"] == "single"
    assert manifest["report_path"] is None
    assert (result.run_dir / "transcript_raw.json").is_file()
    step_names = [s["name"] for s in manifest["steps"]]
    assert "transcribe" in step_names


def test_run_single_full_mocked(tmp_path: Path) -> None:
    audio = tmp_path / "lesson.mp3"
    audio.write_bytes(b"fake-audio")

    def fake_transcribe(input_path, output_path, **kwargs):  # noqa: ANN001
        output_path.write_text(
            json.dumps({"text": "你好世界", "segments": []}, ensure_ascii=False),
            encoding="utf-8",
        )
        return output_path.resolve()

    def fake_correct(input_path, output_path, **kwargs):  # noqa: ANN001
        output_path.write_text("你好，世界。\n", encoding="utf-8")
        return output_path.resolve()

    def fake_structure(corrected_path, output_path, **kwargs):  # noqa: ANN001
        output_path.write_text("## 课程结构与要点\n\n- 开场总：问候\n", encoding="utf-8")
        return output_path.resolve()

    def fake_coach(corrected_path, structure_path, output_path, **kwargs):  # noqa: ANN001
        output_path.write_text(
            "## 结论摘要\n\n结构基本闭合。\n\n## 提升建议\n\n### 合格线（必须改）\n\n| 问题 | 证据摘句 | 改法 |\n",
            encoding="utf-8",
        )
        return output_path.resolve()

    with (
        patch("lesson_review.pipeline.check_llm_api_key") as key_check,
        patch("lesson_review.pipeline.load_llm_config") as load_cfg,
        patch("lesson_review.pipeline.transcribe_audio", side_effect=fake_transcribe),
        patch("lesson_review.pipeline.correct_transcript", side_effect=fake_correct),
        patch("lesson_review.pipeline.analyze_structure", side_effect=fake_structure),
        patch("lesson_review.pipeline.analyze_coach", side_effect=fake_coach),
    ):
        key_check.return_value.ok = True
        load_cfg.return_value.model = "deepseek-v4-flash"
        result = run_single(
            audio,
            output_dir=tmp_path / "out",
            skip_llm=False,
            force=True,
        )

    assert result.report_path is not None
    report = result.report_path.read_text(encoding="utf-8")
    assert "# 课评报告 · 单视频" in report
    assert "## 元信息" in report
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["report_path"] == "report.md"
    assert manifest["llm"]["model"] == "deepseek-v4-flash"


def test_cli_run_requires_llm_without_skip(tmp_path: Path) -> None:
    media = tmp_path / "x.mp3"
    media.write_bytes(b"a")
    with patch("lesson_review.pipeline.check_llm_api_key") as key_check:
        key_check.return_value.ok = False
        key_check.return_value.detail = "LLM_API_KEY missing"
        # Also patch top-level checks so required deps pass
        with patch("lesson_review.cli.run_dependency_checks", return_value=[]):
            result = runner.invoke(app, ["run", str(media), "--force"])
    assert result.exit_code == EXIT_DEPS


def test_cli_run_skip_llm_success(tmp_path: Path) -> None:
    media = tmp_path / "x.mp4"
    media.write_bytes(b"a")

    def fake_extract(input_path, output_path, fmt="mp3", output_root=None):  # noqa: ANN001
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"audio")
        return output_path.resolve()

    def fake_transcribe(input_path, output_path, **kwargs):  # noqa: ANN001
        output_path.write_text(
            json.dumps({"text": "ok", "segments": []}),
            encoding="utf-8",
        )
        return output_path.resolve()

    with (
        patch("lesson_review.cli.run_dependency_checks", return_value=[]),
        patch("lesson_review.pipeline.extract_audio", side_effect=fake_extract),
        patch("lesson_review.pipeline.transcribe_audio", side_effect=fake_transcribe),
    ):
        result = runner.invoke(
            app,
            ["run", str(media), "--skip-llm", "--force", "--output-dir", str(tmp_path / "o")],
        )
    assert result.exit_code == EXIT_OK
    assert "run_id:" in result.stdout

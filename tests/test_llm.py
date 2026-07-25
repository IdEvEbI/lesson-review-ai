"""Tests for prompts loader, LLM client retry, and correct step (mocked)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from lesson_review.checks import EXIT_DEPS, EXIT_PIPELINE, EXIT_USER
from lesson_review.cli import app
from lesson_review.correct import (
    correct_transcript,
    default_corrected_output_path,
    load_transcript_text,
)
from lesson_review.llm import LLMConfig, chat_completion, load_llm_config
from lesson_review.prompts import PROMPT_FILES, combine_system_prompts, load_prompt

runner = CliRunner()


def test_all_prompt_files_load() -> None:
    for name in PROMPT_FILES:
        text = load_prompt(name)
        assert len(text) > 20


def test_combine_system_prompts_includes_punctuation_rule() -> None:
    combined = combine_system_prompts("system_tone", "asr_correct")
    assert "三不" in combined
    assert "补全标点" in combined


def test_default_corrected_output_path_from_raw_json() -> None:
    path = default_corrected_output_path(
        Path("output/demo/transcript_raw.json"),
    )
    assert path == Path("output/demo/transcript_corrected.md")


def test_load_transcript_text_json(tmp_path: Path) -> None:
    raw = {
        "text": "你好世界没有标点",
        "segments": [
            {"start": 0.0, "end": 1.0, "text": "你好"},
            {"start": 1.0, "end": 2.0, "text": "世界"},
        ],
    }
    path = tmp_path / "transcript_raw.json"
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    payload = load_transcript_text(path)
    assert "你好世界没有标点" in payload
    assert "[0.0–1.0] 你好" in payload


def test_load_llm_config_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with patch("lesson_review.llm.getenv", return_value=None):
        with pytest.raises(Exception) as exc_info:
            load_llm_config()
    assert exc_info.value.exit_code == EXIT_DEPS


def test_chat_completion_success() -> None:
    cfg = LLMConfig(
        api_key="sk-test",
        base_url="https://api.example.com",
        model="demo-model",
        max_retries=2,
    )
    fake_message = MagicMock()
    fake_message.content = "纠错后的正文。"
    fake_choice = MagicMock()
    fake_choice.message = fake_message
    fake_response = MagicMock()
    fake_response.choices = [fake_choice]

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_response

    with patch("openai.OpenAI", return_value=fake_client):
        text = chat_completion(system="sys", user="user", config=cfg)

    assert text == "纠错后的正文。"
    fake_client.chat.completions.create.assert_called_once()


def test_chat_completion_retries_on_429() -> None:
    from openai import APIStatusError

    cfg = LLMConfig(
        api_key="sk-secret-should-not-leak",
        base_url="https://api.example.com",
        model="demo-model",
        max_retries=3,
    )

    fake_message = MagicMock()
    fake_message.content = "ok"
    fake_choice = MagicMock()
    fake_choice.message = fake_message
    fake_response = MagicMock()
    fake_response.choices = [fake_choice]

    err = APIStatusError(
        message="rate limit",
        response=MagicMock(status_code=429, headers={}),
        body=None,
    )
    err.status_code = 429

    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [err, fake_response]

    with (
        patch("openai.OpenAI", return_value=fake_client),
        patch("lesson_review.llm.time.sleep"),
    ):
        text = chat_completion(system="s", user="u", config=cfg)

    assert text == "ok"
    assert fake_client.chat.completions.create.call_count == 2


def test_correct_transcript_mocked(tmp_path: Path) -> None:
    raw_path = tmp_path / "transcript_raw.json"
    raw_path.write_text(
        json.dumps({"text": "你好世界", "segments": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    out = tmp_path / "transcript_corrected.md"
    cfg = LLMConfig(
        api_key="sk-test",
        base_url="https://api.example.com",
        model="demo",
    )

    with (
        patch("lesson_review.correct.load_llm_config", return_value=cfg),
        patch(
            "lesson_review.correct.chat_completion",
            return_value="你好，世界。",
        ) as chat_mock,
    ):
        dest = correct_transcript(raw_path, out)

    assert dest == out.resolve()
    assert out.read_text(encoding="utf-8").startswith("你好，世界。")
    chat_mock.assert_called_once()
    assert "补全标点" in chat_mock.call_args.kwargs["system"] or "标点" in chat_mock.call_args.kwargs["system"]


def test_cli_correct_requires_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    raw = tmp_path / "t.json"
    raw.write_text(json.dumps({"text": "hi"}), encoding="utf-8")
    with patch("lesson_review.llm.getenv", return_value=None):
        result = runner.invoke(app, ["correct", str(raw)])
    assert result.exit_code == EXIT_DEPS


def test_cli_correct_success(tmp_path: Path) -> None:
    raw = tmp_path / "transcript_raw.json"
    raw.write_text(json.dumps({"text": "测试"}), encoding="utf-8")
    out = tmp_path / "out.md"
    cfg = LLMConfig(api_key="sk", base_url="https://x", model="m")
    with (
        patch("lesson_review.correct.load_llm_config", return_value=cfg),
        patch("lesson_review.correct.chat_completion", return_value="测试。"),
    ):
        result = runner.invoke(app, ["correct", str(raw), "-o", str(out)])
    assert result.exit_code == 0
    assert str(out.resolve()) in result.stdout

"""Tests for corrected-transcript preamble stripping."""

from __future__ import annotations

from lesson_review.transcript_text import strip_correction_preamble


def test_strip_preamble_with_horizontal_rule() -> None:
    text = (
        "好的，这是对您提供的课堂转写进行纠错和补全标点后的结果。\n"
        "\n"
        "---\n"
        "\n"
        "同学们，我们今天开始学习注意力机制。\n"
    )
    out = strip_correction_preamble(text)
    assert out.startswith("同学们")
    assert "纠错" not in out


def test_strip_keeps_normal_transcript() -> None:
    text = "好，同学们上课了啊。我们先来回顾一下昨天我们讲的课程内容。"
    assert strip_correction_preamble(text) == text

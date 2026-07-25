"""Tests for LLM markdown fence / meta stripping."""

from __future__ import annotations

from lesson_review.markdown_clean import normalize_llm_markdown, strip_markdown_fence


def test_strip_whole_markdown_fence() -> None:
    raw = "```markdown\n## 结论摘要\n\n可读。\n```"
    assert strip_markdown_fence(raw).startswith("## 结论摘要")
    assert "```" not in strip_markdown_fence(raw)


def test_strip_preamble_and_fence() -> None:
    raw = (
        "好的，已收到所有输入。以下是根据系统指令生成的完整 Pass B 内容。\n\n"
        "```markdown\n## 结论摘要\n\n可读。\n\n## 优先改进 Top 3\n```\n"
    )
    out = normalize_llm_markdown(raw)
    assert out.startswith("## 结论摘要")
    assert "```" not in out
    assert "已收到" not in out


def test_structure_fence() -> None:
    raw = "```markdown\n## 课程结构与要点\n\n- 开场总：示例\n```"
    out = normalize_llm_markdown(raw)
    assert out.startswith("## 课程结构与要点")

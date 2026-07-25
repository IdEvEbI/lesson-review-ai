"""Tests for Pass B coach / suggestions split."""

from __future__ import annotations

from lesson_review.analyze import split_pass_b_markdown


def test_split_pass_b_keeps_coach_short() -> None:
    raw = """## 结论摘要

可读。

## 优先改进 Top 3

| 排序 | 类型 | 问题 | 证据摘句 | 改法 |
| ---- | ---- | ---- | -------- | ---- |

## 教学能力摘要（授课力 · 本步展开 V1–V4）

- V1 专业力：示例
- V5 / V6：本步不展开（非本版门禁）

## 提升建议

### 合格线（必须改）

| 问题 | 证据摘句 | 改法 |
| ---- | -------- | ---- |

## 待回放确认（转写无法判定）

| 项 | 为何无法仅凭稿判断 | 建议回放关注点 |
| -- | ------------------ | -------------- |
"""
    coach, suggestions = split_pass_b_markdown(raw)
    assert "## 结论摘要" in coach
    assert "## 教学能力摘要" in coach
    assert "## 提升建议" not in coach
    assert "## 待回放确认" not in coach
    assert suggestions.startswith("## 提升建议")
    assert "## 待回放确认" in suggestions

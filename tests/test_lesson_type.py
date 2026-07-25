"""Tests for lesson_type inference."""

from __future__ import annotations

from lesson_review.lesson_type import infer_lesson_type, normalize_lesson_type


def test_infer_principle_from_qkv_title() -> None:
    assert infer_lesson_type("注意力机制_QKV简介")[0] == "principle"


def test_infer_code_from_title() -> None:
    assert infer_lesson_type("03-注意力机制代码实现")[0] == "code"


def test_infer_lab_from_title() -> None:
    assert infer_lesson_type("04-动手实操-跟做")[0] == "lab"


def test_normalize_aliases() -> None:
    assert normalize_lesson_type("原理") == "principle"
    assert normalize_lesson_type("CODE") == "code"
    assert normalize_lesson_type("weird", default="lab") == "lab"

"""Tests for lesson_type inference."""

from __future__ import annotations

import pytest

from lesson_review.lesson_type import (
    LessonTypeError,
    infer_lesson_type,
    normalize_lesson_type,
    parse_lesson_type_cli,
)


def test_infer_principle_from_qkv_title() -> None:
    assert infer_lesson_type("注意力机制_QKV简介")[0] == "principle"


def test_infer_code_from_title() -> None:
    assert infer_lesson_type("03-注意力机制代码实现")[0] == "code"


def test_infer_lab_from_title() -> None:
    assert infer_lesson_type("04-动手实操-跟做")[0] == "lab"


def test_infer_lab_from_install_title() -> None:
    assert infer_lesson_type("0725-时勇霞-001-python 解释器安装")[0] == "lab"
    assert infer_lesson_type("安装 MySQL")[0] == "lab"
    assert infer_lesson_type("虚拟机安装")[0] == "lab"


def test_infer_lab_beats_principle_when_both_match() -> None:
    assert infer_lesson_type("虚拟机环境介绍")[0] == "lab"
    assert infer_lesson_type("Python 环境配置简介")[0] == "lab"


def test_normalize_aliases() -> None:
    assert normalize_lesson_type("原理") == "principle"
    assert normalize_lesson_type("CODE") == "code"
    assert normalize_lesson_type("weird", default="lab") == "lab"
    assert normalize_lesson_type("安装") == "lab"


def test_parse_cli_rejects_typo_lib() -> None:
    with pytest.raises(LessonTypeError, match="lab"):
        parse_lesson_type_cli("lib")


def test_parse_cli_accepts_lab() -> None:
    assert parse_lesson_type_cli("lab") == "lab"
    assert parse_lesson_type_cli("实操") == "lab"

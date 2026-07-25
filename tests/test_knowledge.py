"""Tests for Pass A knowledge review gates."""

from __future__ import annotations

from lesson_review.knowledge import (
    extract_json_object,
    infer_anchor_strength,
    qualifying_issues,
    sanitize_knowledge_review,
)


def test_infer_anchor_strength_weak_day_title() -> None:
    assert infer_anchor_strength("day01") == "weak"
    assert infer_anchor_strength("注意力机制概念介绍") == "strong"


def test_extract_json_from_fence() -> None:
    text = '前言\n```json\n{"schema_version": 1, "findings": []}\n```\n'
    data = extract_json_object(text)
    assert data["schema_version"] == 1


def test_sanitize_demotes_issue_without_quote() -> None:
    raw = {
        "summary": "x",
        "anchor_strength": "strong",
        "findings": [
            {
                "id": "k1",
                "category": "accuracy",
                "claim": "疑似讲错",
                "evidence": {"quote": ""},
                "verdict": "issue",
                "confidence": "high",
            }
        ],
    }
    out = sanitize_knowledge_review(raw, title_anchor="注意力机制概念介绍")
    assert out["findings"][0]["verdict"] == "unverified"
    assert qualifying_issues(out) == []


def test_sanitize_coverage_gap_forced_unverified() -> None:
    raw = {
        "summary": "x",
        "findings": [
            {
                "id": "k2",
                "category": "coverage_gap",
                "claim": "标题有但未讲",
                "evidence": {"quote": "……"},
                "verdict": "issue",
                "confidence": "high",
            }
        ],
    }
    out = sanitize_knowledge_review(raw, title_anchor="注意力机制概念介绍")
    assert out["findings"][0]["verdict"] == "unverified"
    assert qualifying_issues(out) == []


def test_qualifying_issue_with_quote() -> None:
    raw = {
        "summary": "x",
        "anchor_strength": "strong",
        "findings": [
            {
                "id": "k3",
                "category": "case",
                "claim": "案例未回扣",
                "evidence": {"quote": "我们举个买菜的例子"},
                "verdict": "issue",
                "confidence": "high",
                "remediation": "回扣到注意力权重",
            }
        ],
    }
    out = sanitize_knowledge_review(raw, title_anchor="注意力机制概念介绍")
    issues = qualifying_issues(out)
    assert len(issues) == 1
    assert issues[0]["id"] == "k3"


def test_qualifying_clarity_issue_with_quote() -> None:
    raw = {
        "summary": "QKV 关系未讲清",
        "anchor_strength": "strong",
        "findings": [
            {
                "id": "k5",
                "category": "clarity",
                "claim": "仅有类比，未说明 Q 对 K 匹配与加权 V",
                "evidence": {"quote": "我们介绍了注意力机制该如何实现吧？我们提到了 QKV"},
                "verdict": "issue",
                "confidence": "high",
                "remediation": "补一句：Q 与各 K 算相似度得权重，再对 V 加权求和",
            }
        ],
    }
    out = sanitize_knowledge_review(raw, title_anchor="注意力机制_QKV简介")
    issues = qualifying_issues(out)
    assert len(issues) == 1
    assert issues[0]["category"] == "clarity"


def test_unknown_category_falls_back_to_accuracy() -> None:
    raw = {
        "summary": "x",
        "findings": [
            {
                "id": "k6",
                "category": "unknown_cat",
                "claim": "x",
                "evidence": {"quote": "一句"},
                "verdict": "pass",
                "confidence": "high",
            }
        ],
    }
    out = sanitize_knowledge_review(raw, title_anchor="注意力机制概念介绍")
    assert out["findings"][0]["category"] == "accuracy"


def test_weak_anchor_blocks_high_issue() -> None:
    raw = {
        "summary": "x",
        "anchor_strength": "weak",
        "findings": [
            {
                "id": "k4",
                "category": "accuracy",
                "claim": "可能不准",
                "evidence": {"quote": "一段话"},
                "verdict": "issue",
                "confidence": "high",
            }
        ],
    }
    out = sanitize_knowledge_review(raw, title_anchor="day01")
    assert out["findings"][0]["verdict"] == "unverified"
    assert qualifying_issues(out) == []

"""Tests for batch sorting and conduct heuristics."""

from __future__ import annotations

from pathlib import Path

from lesson_review.batch import _render_summary, list_media_sorted, sort_key_media
from lesson_review.batch import BatchItemResult
from lesson_review.conduct import heuristic_hints


def test_sort_key_numeric_prefix() -> None:
    assert sort_key_media(Path("01-foo.mp4")) < sort_key_media(Path("02-bar.mp4"))
    assert sort_key_media(Path("2-x.mp4")) < sort_key_media(Path("10-y.mp4"))


def test_list_media_sorted(tmp_path: Path) -> None:
    (tmp_path / "10-b.mp4").write_bytes(b"x")
    (tmp_path / "02-a.mp4").write_bytes(b"x")
    (tmp_path / "readme.txt").write_text("no", encoding="utf-8")
    names = [p.name for p in list_media_sorted(tmp_path)]
    assert names == ["02-a.mp4", "10-b.mp4"]


def test_heuristic_hints_profanity_belittle_teacher_and_subject() -> None:
    text = "卧槽，上一个老师讲得不好，这门课没用，我们重讲。"
    hints = heuristic_hints(text)
    assert "卧槽" in hints["profanity_hints"]
    assert hints["belittle_prior_teacher_hints"]
    assert hints["belittle_hints"]  # alias
    assert hints["belittle_subject_or_course_hints"]


def test_render_summary_includes_disposition() -> None:
    items = [
            BatchItemResult(
                index=1,
                stem="01-demo",
                input_path=Path("01-demo.mp4"),
                item_dir=Path("01_01-demo"),
                status="ok",
                finding_count=1,
            )
    ]
    scans = [
        {
            "summary": "发现脏话。",
            "findings": [
                {
                    "category": "profanity",
                    "claim": "出现粗口",
                    "evidence": {"quote": "卧槽"},
                    "confidence": "high",
                    "disposition_path": "private_align",
                }
            ],
        }
    ]
    md = _render_summary("conduct_test", items, scans)
    assert "建议处置" in md
    assert "`private_align`" in md
    assert "`profanity`" in md

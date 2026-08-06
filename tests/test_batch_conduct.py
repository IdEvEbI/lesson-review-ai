"""Tests for batch sorting, duration helpers, and summary enrichment."""

from __future__ import annotations

import json
from pathlib import Path

from lesson_review.batch import (
    BatchItemResult,
    _render_summary,
    batch_id_from_input_dir,
    duration_from_transcript,
    list_media_sorted,
    sort_key_media,
)
from lesson_review.conduct import heuristic_hints
from lesson_review.outline import format_duration
from lesson_review.pedagogy import normalize_pedagogy_type


def test_sort_key_numeric_prefix() -> None:
    assert sort_key_media(Path("01-foo.mp4")) < sort_key_media(Path("02-bar.mp4"))
    assert sort_key_media(Path("2-x.mp4")) < sort_key_media(Path("10-y.mp4"))


def test_list_media_sorted(tmp_path: Path) -> None:
    (tmp_path / "10-b.mp4").write_bytes(b"x")
    (tmp_path / "02-a.mp4").write_bytes(b"x")
    (tmp_path / "readme.txt").write_text("no", encoding="utf-8")
    names = [p.name for p in list_media_sorted(tmp_path)]
    assert names == ["02-a.mp4", "10-b.mp4"]


def test_batch_id_from_input_dir_uses_folder_name() -> None:
    assert (
        batch_id_from_input_dir(Path("data/input/day01-project-rf-2026-07-23"))
        == "day01-project-rf-2026-07-23"
    )
    assert batch_id_from_input_dir(Path("data/input/课例目录-day01")) == "课例目录-day01"


def test_batch_id_from_input_dir_fallback_for_dot() -> None:
    batch_id = batch_id_from_input_dir(Path("."))
    assert batch_id.startswith("conduct_")
    assert len(batch_id) > len("conduct_")


def test_duration_from_transcript(tmp_path: Path) -> None:
    path = tmp_path / "transcript_raw.json"
    path.write_text(
        json.dumps(
            {
                "segments": [
                    {"start": 0.0, "end": 1.5, "text": "a"},
                    {"start": 1.5, "end": 125.25, "text": "b"},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert duration_from_transcript(path) == 125.25


def test_format_duration() -> None:
    assert format_duration(65) == "1:05"
    assert format_duration(3661) == "1:01:01"
    assert format_duration(None) == "—"


def test_normalize_pedagogy_type() -> None:
    assert normalize_pedagogy_type("004") == "004"
    assert normalize_pedagogy_type("4") == "004"
    assert normalize_pedagogy_type("nope") == "other"


def test_heuristic_hints_profanity_belittle_teacher_and_subject() -> None:
    text = "卧槽，上一个老师讲得不好，这门课没用，我们重讲。"
    hints = heuristic_hints(text)
    assert "卧槽" in hints["profanity_hints"]
    assert hints["belittle_prior_teacher_hints"]
    assert hints["belittle_hints"]  # alias
    assert hints["belittle_subject_or_course_hints"]


def test_render_summary_includes_duration_and_pedagogy() -> None:
    items = [
        BatchItemResult(
            index=1,
            stem="01-demo",
            input_path=Path("01-demo.mp4"),
            item_dir=Path("01_01-demo"),
            status="ok",
            media_duration_s=125.0,
            pedagogy_type="004",
            pedagogy_type_source="llm",
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
    md = _render_summary("demo-batch", items, scans)
    assert "成功段合计时长" in md
    assert "2:05" in md  # 125s
    assert "`004`" in md
    assert "细课型日分布" in md
    assert "建议处置" in md
    assert "`private_align`" in md

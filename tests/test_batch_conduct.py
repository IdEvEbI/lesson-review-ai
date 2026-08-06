"""Tests for batch sorting and conduct heuristics."""

from __future__ import annotations

from pathlib import Path

from lesson_review.batch import list_media_sorted, sort_key_media
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


def test_heuristic_hints_profanity_and_belittle() -> None:
    text = "卧槽，上一个老师讲得不好，我们重讲。"
    hints = heuristic_hints(text)
    assert "卧槽" in hints["profanity_hints"]
    assert hints["belittle_hints"]

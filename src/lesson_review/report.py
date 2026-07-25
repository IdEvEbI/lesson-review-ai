"""Render single-video report.md from pipeline artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def render_single_report(
    *,
    run_id: str,
    input_path: Path,
    structure_md: str,
    coach_md: str,
    corrected_relpath: str,
    generated_at: datetime | None = None,
) -> str:
    """Assemble report markdown matching the report contract skeleton."""
    when = generated_at or datetime.now(timezone.utc)
    stamp = when.astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    structure_body = structure_md.strip() or "（结构要点为空）"
    coach_body = coach_md.strip() or "（提升建议为空）"

    parts = [
        "# 课评报告 · 单视频",
        "",
        "## 元信息",
        "",
        f"- 输入文件：`{input_path}`",
        f"- 运行 ID：`{run_id}`",
        f"- 生成时间：{stamp}",
        "",
        structure_body,
        "",
        coach_body,
        "",
        "## 附录",
        "",
        f"- 纠错逐字稿：`{corrected_relpath}`",
        "",
    ]
    return "\n".join(parts)

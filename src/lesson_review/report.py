"""Render single-video report.md from pipeline artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lesson_review.lesson_type import LESSON_TYPE_LABELS


def _quote(evidence: Any) -> str:
    if isinstance(evidence, dict):
        return str(evidence.get("quote") or "").strip()
    if isinstance(evidence, str):
        return evidence.strip()
    return ""


def _format_finding_lines(items: list[dict[str, Any]]) -> list[str]:
    if not items:
        return ["- （无）"]
    lines: list[str] = []
    for item in items:
        claim = str(item.get("claim") or "").strip() or "（无说明）"
        quote = _quote(item.get("evidence"))
        verdict = item.get("verdict")
        confidence = item.get("confidence")
        rem = item.get("remediation")
        line = f"- [{verdict}/{confidence}] {claim}"
        if quote:
            line += f" 证据：「{quote}」"
        if isinstance(rem, str) and rem.strip():
            line += f" 改法：{rem.strip()}"
        lines.append(line)
    return lines


def render_knowledge_sections(review: dict[str, Any]) -> str:
    """Deterministic Markdown for Pass A findings (gates already applied)."""
    findings = [f for f in (review.get("findings") or []) if isinstance(f, dict)]
    accuracy = [f for f in findings if f.get("category") == "accuracy"]
    clarity = [f for f in findings if f.get("category") == "clarity"]
    cases = [f for f in findings if f.get("category") == "case"]
    pending = [
        f
        for f in findings
        if f.get("category") == "coverage_gap"
        or f.get("verdict") == "unverified"
        or f.get("confidence") == "low"
    ]
    parts = [
        "## 专业预审（知识、讲清度与案例）",
        "",
        f"- 预审摘要：{review.get('summary') or '（无）'}",
        f"- 标题锚点强度：`{review.get('anchor_strength')}`",
        "",
        "### 知识准确性",
        "",
        *_format_finding_lines(accuracy),
        "",
        "### 讲清度（核心关系 / 机制）",
        "",
        *_format_finding_lines(clarity),
        "",
        "### 案例恰当性",
        "",
        *_format_finding_lines(cases),
        "",
        "### 待核实",
        "",
        *_format_finding_lines(pending),
        "",
    ]
    return "\n".join(parts)


def render_single_report(
    *,
    run_id: str,
    input_path: Path,
    title_anchor: str,
    knowledge_review: dict[str, Any],
    structure_md: str,
    coach_md: str,
    corrected_relpath: str,
    knowledge_relpath: str = "knowledge_review.json",
    suggestions_md: str | None = None,
    outline_md: str | None = None,
    outline_relpath: str = "teaching_outline.md",
    lesson_type: str | None = None,
    lesson_type_source: str | None = None,
    generated_at: datetime | None = None,
) -> str:
    """Assemble report markdown matching the report contract skeleton."""
    when = generated_at or datetime.now(timezone.utc)
    stamp = when.astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    structure_body = structure_md.strip() or "（结构要点为空）"
    coach_body = coach_md.strip() or "（教练摘要为空）"
    suggestions_body = (suggestions_md or "").strip()
    knowledge_body = render_knowledge_sections(knowledge_review)
    outline_body = (outline_md or "").strip()
    lesson_label = LESSON_TYPE_LABELS.get(lesson_type or "", lesson_type or "（未设）")

    parts = [
        "# 课评报告 · 单视频",
        "",
        "## 元信息",
        "",
        f"- 输入文件：`{input_path}`",
        f"- 标题锚点：`{title_anchor}`",
        f"- 课型：`{lesson_type or 'principle'}`（{lesson_label}；来源：`{lesson_type_source or 'inferred'}`）",
        f"- 运行 ID：`{run_id}`",
        f"- 生成时间：{stamp}",
        "- 说明：专业判断仅基于转写与标题锚点，不是对照完整讲义的判分；"
        "共屏画面与未入稿内容见「待回放确认」（本仓默认非黑板板书）；"
        "授课力本步仅展开 V1–V4；讲解提纲为参考，非标准讲义；"
        "`coach.md` 为发给老师的短稿（结论 / Top3 / 四维），合格线与待回放仅在本报告。",
        "",
        coach_body,
        "",
    ]
    if suggestions_body:
        parts.extend([suggestions_body, ""])
    parts.extend(
        [
            knowledge_body,
            structure_body,
            "",
        ]
    )
    if outline_body:
        parts.extend(
            [
                "## 讲解重点提纲（摘录）",
                "",
                outline_body,
                "",
            ]
        )
    parts.extend(
        [
            "## 附录",
            "",
            f"- 纠错逐字稿：`{corrected_relpath}`",
            f"- 专业预审：`{knowledge_relpath}`",
            "- 教练短稿（可发老师）：`coach.md`",
            "- 合格线/待回放：`suggestions.md`",
            "- 结构要点：`structure.md`",
            f"- 讲解重点提纲：`{outline_relpath}`",
            "",
        ]
    )
    return "\n".join(parts)

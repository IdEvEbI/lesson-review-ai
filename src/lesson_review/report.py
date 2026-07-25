"""Render single-video report.md from pipeline artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
    generated_at: datetime | None = None,
) -> str:
    """Assemble report markdown matching the report contract skeleton."""
    when = generated_at or datetime.now(timezone.utc)
    stamp = when.astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    structure_body = structure_md.strip() or "（结构要点为空）"
    coach_body = coach_md.strip() or "（提升建议为空）"
    knowledge_body = render_knowledge_sections(knowledge_review)

    parts = [
        "# 课评报告 · 单视频",
        "",
        "## 元信息",
        "",
        f"- 输入文件：`{input_path}`",
        f"- 标题锚点：`{title_anchor}`",
        f"- 运行 ID：`{run_id}`",
        f"- 生成时间：{stamp}",
        "- 说明：专业判断仅基于转写与标题锚点，不是对照完整讲义的判分；"
        "公屏画面与未入稿内容见「待回放确认」（本仓默认非黑板板书）。",
        "",
        coach_body,
        "",
        knowledge_body,
        structure_body,
        "",
        "## 附录",
        "",
        f"- 纠错逐字稿：`{corrected_relpath}`",
        f"- 专业预审：`{knowledge_relpath}`",
        "",
    ]
    return "\n".join(parts)

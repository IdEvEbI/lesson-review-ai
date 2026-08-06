"""Lightweight batch outline for scatter / mainline checks."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from lesson_review.checks import EXIT_PIPELINE, EXIT_USER
from lesson_review.llm import LLMError, chat_completion, load_llm_config
from lesson_review.prompts import PromptError, combine_system_prompts
from lesson_review.transcript_text import strip_correction_preamble


class OutlineError(Exception):
    """Raised when batch outline cannot complete."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _parse_json_object(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned, flags=re.IGNORECASE)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise OutlineError("batch outline response is not valid JSON", EXIT_PIPELINE)
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise OutlineError(
                f"batch outline JSON parse failed: {exc}",
                EXIT_PIPELINE,
            ) from exc
    if not isinstance(data, dict):
        raise OutlineError("batch outline JSON must be an object", EXIT_PIPELINE)
    return data


def analyze_batch_outline(
    corrected_path: Path,
    output_json: Path,
    output_md: Path,
    *,
    title_anchor: str,
    model: str | None = None,
) -> dict[str, Any]:
    """Write outline JSON + short markdown for one batch item."""
    if not corrected_path.is_file():
        raise OutlineError(f"corrected transcript missing: {corrected_path}", EXIT_USER)
    text = strip_correction_preamble(corrected_path.read_text(encoding="utf-8"))
    if not text.strip():
        raise OutlineError(f"corrected transcript empty: {corrected_path}", EXIT_USER)

    max_chars = 24000
    if len(text) > max_chars:
        head = text[: max_chars // 2]
        tail = text[-(max_chars // 2) :]
        text = head + "\n\n…(中间省略)…\n\n" + tail

    user = "\n".join(
        [
            f"title_anchor: {title_anchor}",
            "请只输出 JSON（nodes 5～12；见系统提示词）。",
            "",
            "## 纠错逐字稿",
            text,
        ]
    )
    try:
        system = combine_system_prompts("system_tone", "batch_outline")
        cfg = load_llm_config(model=model)
        content = chat_completion(system=system, user=user, config=cfg)
        payload = _parse_json_object(content)
    except PromptError as exc:
        raise OutlineError(str(exc), EXIT_USER) from exc
    except LLMError as exc:
        raise OutlineError(str(exc), exc.exit_code) from exc

    nodes_raw = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
    nodes: list[dict[str, Any]] = []
    for node in nodes_raw[:12]:
        if not isinstance(node, dict):
            continue
        title = str(node.get("title") or "").strip()
        if not title:
            continue
        entry: dict[str, Any] = {
            "title": title,
            "one_liner": str(node.get("one_liner") or "").strip(),
        }
        start = node.get("start_s")
        if isinstance(start, (int, float)) and start >= 0:
            entry["start_s"] = float(start)
        nodes.append(entry)

    result = {
        "schema_version": 1,
        "title_anchor": title_anchor,
        "nodes": nodes,
        "mainline": str(payload.get("mainline") or "").strip(),
        "scatter_note": str(payload.get("scatter_note") or "").strip(),
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output_md.write_text(render_outline_markdown(result), encoding="utf-8")
    return result


def render_outline_markdown(payload: dict[str, Any]) -> str:
    """Render a short markdown outline from outline JSON."""
    lines = [
        f"# 讲解结构 · {payload.get('title_anchor') or ''}".rstrip(),
        "",
    ]
    mainline = str(payload.get("mainline") or "").strip()
    if mainline:
        lines.append(f"- **主线**：{mainline}")
    scatter = str(payload.get("scatter_note") or "").strip()
    if scatter:
        lines.append(f"- **散点观察**：{scatter}")
    if mainline or scatter:
        lines.append("")
    lines.append("## 节点")
    lines.append("")
    nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
    if not nodes:
        lines.append("（未提炼到节点）")
        lines.append("")
        return "\n".join(lines)
    for index, node in enumerate(nodes, start=1):
        if not isinstance(node, dict):
            continue
        title = str(node.get("title") or "").strip() or f"节点 {index}"
        start = node.get("start_s")
        prefix = f"{index}. "
        if isinstance(start, (int, float)):
            prefix = f"{index}. [`{format_duration(float(start))}`] "
        one = str(node.get("one_liner") or "").strip()
        lines.append(f"{prefix}**{title}**" + (f" — {one}" if one else ""))
    lines.append("")
    return "\n".join(lines)


def format_duration(seconds: float | None) -> str:
    """Format seconds as H:MM:SS or M:SS."""
    if seconds is None or seconds < 0:
        return "—"
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"

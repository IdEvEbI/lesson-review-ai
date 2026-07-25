"""LLM analysis steps: structure and coach feedback (Pass B)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from lesson_review.checks import EXIT_USER
from lesson_review.knowledge import qualifying_issues
from lesson_review.lesson_type import LESSON_TYPE_LABELS, normalize_lesson_type
from lesson_review.llm import LLMError, chat_completion, load_llm_config
from lesson_review.markdown_clean import normalize_llm_markdown
from lesson_review.prompts import PromptError, combine_system_prompts
from lesson_review.transcript_text import strip_correction_preamble


class AnalyzeError(Exception):
    """Raised when structure or coach analysis fails."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _read_corrected(path: Path) -> str:
    if not path.is_file():
        raise AnalyzeError(f"corrected transcript missing: {path}", EXIT_USER)
    text = strip_correction_preamble(path.read_text(encoding="utf-8"))
    if not text:
        raise AnalyzeError(f"corrected transcript empty: {path}", EXIT_USER)
    return text


def analyze_structure(
    corrected_path: Path,
    output_path: Path,
    *,
    model: str | None = None,
) -> Path:
    """Write structure markdown using structure_single prompt."""
    corrected = _read_corrected(corrected_path)
    try:
        system = combine_system_prompts("system_tone", "structure_single")
        cfg = load_llm_config(model=model)
        content = chat_completion(
            system=system,
            user=(
                "请根据下列纠错逐字稿，提炼总分总与小闭环/递进。"
                "不要判定知识对错或案例好坏。"
                "直接输出 Markdown 正文，不要用代码块包裹。\n\n"
                + corrected
            ),
            config=cfg,
        )
    except PromptError as exc:
        raise AnalyzeError(str(exc), EXIT_USER) from exc
    except LLMError as exc:
        raise AnalyzeError(str(exc), exc.exit_code) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    body = normalize_llm_markdown(content)
    body = body if body.endswith("\n") else body + "\n"
    output_path.write_text(body, encoding="utf-8")
    return output_path.resolve()


def split_pass_b_markdown(content: str) -> tuple[str, str]:
    """Split Pass B markdown into slim coach.md and suggestions.md bodies.

    Coach keeps 结论摘要 / Top3 / 教学能力摘要.
    Suggestions keeps 提升建议 / 待回放确认 (report-only).
    """
    text = content.strip()
    if not text:
        return "", ""

    match = re.search(r"(?m)^##\s*提升建议\s*$", text)
    if not match:
        # Fallback: keep all in coach if model omitted the split heading.
        return text + "\n", ""

    coach = text[: match.start()].rstrip() + "\n"
    suggestions = text[match.start() :].strip() + "\n"
    return coach, suggestions


def analyze_coach(
    corrected_path: Path,
    structure_path: Path,
    knowledge_path: Path,
    output_path: Path,
    *,
    suggestions_path: Path | None = None,
    model: str | None = None,
) -> tuple[Path, Path]:
    """Write slim coach.md and suggestions.md (提升建议 + 待回放)."""
    corrected = _read_corrected(corrected_path)
    if not structure_path.is_file():
        raise AnalyzeError(f"structure file missing: {structure_path}", EXIT_USER)
    if not knowledge_path.is_file():
        raise AnalyzeError(f"knowledge review missing: {knowledge_path}", EXIT_USER)
    structure = structure_path.read_text(encoding="utf-8").strip()
    knowledge_raw = knowledge_path.read_text(encoding="utf-8").strip()
    try:
        knowledge_obj = json.loads(knowledge_raw)
        knowledge_pretty = json.dumps(knowledge_obj, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        knowledge_pretty = knowledge_raw

    suggestions_dest = suggestions_path or (output_path.parent / "suggestions.md")

    user = "\n".join(
        [
            "请消费下列 Pass A JSON 与结构要点，撰写 Pass B 全部五节（按提示词顺序）。",
            "知识/讲清度/案例必改项只能来自 Pass A 中 "
            "accuracy|clarity|case 且 issue+high+有摘句的条目。",
            "须含「提升建议」与「待回放确认」节；遵守表达噪声闸门与 Top3 权重。",
            "教学能力仅展开 V1–V4；V5/V6 写本步不展开。",
            "授课媒介为公屏（PPT/笔记/IDE），改法禁止默认板书。",
            "直接输出 Markdown 正文，不要用 ```markdown 代码块包裹，不要写前言。",
            "",
            "## Pass A knowledge_review.json",
            knowledge_pretty,
            "",
            "## 结构要点",
            structure or "（空）",
            "",
            "## 纠错逐字稿",
            corrected,
        ]
    )
    try:
        system = combine_system_prompts("system_tone", "coach_feedback")
        cfg = load_llm_config(model=model)
        content = chat_completion(system=system, user=user, config=cfg)
    except PromptError as exc:
        raise AnalyzeError(str(exc), EXIT_USER) from exc
    except LLMError as exc:
        raise AnalyzeError(str(exc), exc.exit_code) from exc

    coach_body, suggestions_body = split_pass_b_markdown(normalize_llm_markdown(content))
    if not suggestions_body.strip():
        suggestions_body = (
            "## 提升建议\n\n（模型未输出本节；请回放或重跑 Pass B。）\n\n"
            "## 待回放确认（转写无法判定）\n\n"
            "| 项 | 为何无法仅凭稿判断 | 建议回放关注点 |\n"
            "| -- | ------------------ | -------------- |\n"
            "| （无） | 模型未输出待回放节 | 对照公屏回放确认 |\n"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    coach_out = coach_body if coach_body.endswith("\n") else coach_body + "\n"
    sug_out = (
        suggestions_body
        if suggestions_body.endswith("\n")
        else suggestions_body + "\n"
    )
    output_path.write_text(coach_out, encoding="utf-8")
    suggestions_dest.write_text(sug_out, encoding="utf-8")
    return output_path.resolve(), suggestions_dest.resolve()


def _format_avoid_issues(knowledge_obj: object) -> str:
    if not isinstance(knowledge_obj, dict):
        return "（Pass A 无法解析；不要编造须回避项。）"
    issues = qualifying_issues(knowledge_obj)
    if not issues:
        return "本段 Pass A 无高置信 issue；写「本段 Pass A 无高置信 issue」。"
    lines: list[str] = []
    for item in issues:
        claim = str(item.get("claim") or "").strip()
        evidence = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
        quote = ""
        if isinstance(evidence, dict):
            quote = str(evidence.get("quote") or "").strip()
        rem = item.get("remediation")
        rem_text = rem.strip() if isinstance(rem, str) else ""
        chunk = f"- [{item.get('category')}] {claim}"
        if quote:
            chunk += f" 摘句：「{quote}」"
        if rem_text:
            chunk += f" 改写方向：{rem_text}"
        lines.append(chunk)
    return "\n".join(lines)


def analyze_teaching_outline(
    corrected_path: Path,
    structure_path: Path,
    knowledge_path: Path,
    output_path: Path,
    *,
    title_anchor: str,
    lesson_type: str,
    model: str | None = None,
) -> Path:
    """Write teaching_outline.md (key-point outline; avoid Pass A issues)."""
    corrected = _read_corrected(corrected_path)
    if not structure_path.is_file():
        raise AnalyzeError(f"structure file missing: {structure_path}", EXIT_USER)
    if not knowledge_path.is_file():
        raise AnalyzeError(f"knowledge review missing: {knowledge_path}", EXIT_USER)
    structure = structure_path.read_text(encoding="utf-8").strip()
    knowledge_raw = knowledge_path.read_text(encoding="utf-8").strip()
    try:
        knowledge_obj = json.loads(knowledge_raw)
    except json.JSONDecodeError:
        knowledge_obj = None
    lesson = normalize_lesson_type(lesson_type)
    label = LESSON_TYPE_LABELS.get(lesson, lesson)
    avoid_block = _format_avoid_issues(knowledge_obj)

    user = "\n".join(
        [
            f"title_anchor: {title_anchor}",
            f"lesson_type: {lesson}（{label}）",
            "请输出讲解重点提纲 Markdown（偏提纲，非全文示范课）。",
            "必须回避下列 Pass A issue；公屏授课，禁止默认板书。",
            "直接输出 Markdown 正文，不要用代码块包裹，不要写前言。",
            "",
            "## 须回避的 Pass A issue",
            avoid_block,
            "",
            "## 结构要点",
            structure or "（空）",
            "",
            "## 纠错逐字稿",
            corrected,
        ]
    )
    try:
        system = combine_system_prompts("system_tone", "teaching_outline")
        cfg = load_llm_config(model=model)
        content = chat_completion(system=system, user=user, config=cfg)
    except PromptError as exc:
        raise AnalyzeError(str(exc), EXIT_USER) from exc
    except LLMError as exc:
        raise AnalyzeError(str(exc), exc.exit_code) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    body = normalize_llm_markdown(content)
    body = body if body.endswith("\n") else body + "\n"
    output_path.write_text(body, encoding="utf-8")
    return output_path.resolve()

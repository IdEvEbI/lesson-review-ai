"""LLM analysis steps: structure and coach feedback (Pass B)."""

from __future__ import annotations

import json
from pathlib import Path

from lesson_review.checks import EXIT_USER
from lesson_review.llm import LLMError, chat_completion, load_llm_config
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
                "不要判定知识对错或案例好坏。\n\n"
                + corrected
            ),
            config=cfg,
        )
    except PromptError as exc:
        raise AnalyzeError(str(exc), EXIT_USER) from exc
    except LLMError as exc:
        raise AnalyzeError(str(exc), exc.exit_code) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    body = content if content.endswith("\n") else content + "\n"
    output_path.write_text(body, encoding="utf-8")
    return output_path.resolve()


def analyze_coach(
    corrected_path: Path,
    structure_path: Path,
    knowledge_path: Path,
    output_path: Path,
    *,
    model: str | None = None,
) -> Path:
    """Write coach feedback markdown using coach_feedback prompt (Pass B)."""
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

    user = "\n".join(
        [
            "请消费下列 Pass A JSON 与结构要点，撰写 Pass B 报告段落。",
            "知识/讲清度/案例必改项只能来自 Pass A 中 "
            "accuracy|clarity|case 且 issue+high+有摘句的条目。",
            "须含「待回放确认」节；遵守表达噪声闸门与 Top3 权重。",
            "教学能力仅展开 V1–V4；V5/V6 写本步不展开。",
            "授课媒介为公屏（PPT/笔记/IDE），改法禁止默认板书。",
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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    body = content if content.endswith("\n") else content + "\n"
    output_path.write_text(body, encoding="utf-8")
    return output_path.resolve()

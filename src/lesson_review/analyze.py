"""LLM analysis steps: structure and coach feedback."""

from __future__ import annotations

from pathlib import Path

from lesson_review.checks import EXIT_USER
from lesson_review.llm import LLMError, chat_completion, load_llm_config
from lesson_review.prompts import PromptError, combine_system_prompts


class AnalyzeError(Exception):
    """Raised when structure or coach analysis fails."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _read_corrected(path: Path) -> str:
    if not path.is_file():
        raise AnalyzeError(f"corrected transcript missing: {path}", EXIT_USER)
    text = path.read_text(encoding="utf-8").strip()
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
            user="请根据下列纠错逐字稿，提炼单视频课程结构与要点。\n\n" + corrected,
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
    output_path: Path,
    *,
    model: str | None = None,
) -> Path:
    """Write coach feedback markdown using coach_feedback prompt."""
    corrected = _read_corrected(corrected_path)
    if not structure_path.is_file():
        raise AnalyzeError(f"structure file missing: {structure_path}", EXIT_USER)
    structure = structure_path.read_text(encoding="utf-8").strip()

    user = "\n".join(
        [
            "请根据纠错逐字稿与结构要点，撰写结论摘要与提升建议（合格线 / 水平线分开）。",
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

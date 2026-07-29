"""Classroom conduct scan: profanity and belittling prior teachers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from lesson_review.checks import EXIT_PIPELINE, EXIT_USER
from lesson_review.llm import LLMError, chat_completion, load_llm_config
from lesson_review.prompts import PromptError, combine_system_prompts
from lesson_review.transcript_text import strip_correction_preamble

# Soft prefilter hints for the model / summary (not a verdict by themselves).
_PROFANITY_HINT = re.compile(
    r"(卧槽|我操|我草|他妈|特么|妈的|他妈的|傻逼|傻B|牛逼|牛B|尼玛|你妈的|艹|靠逼)",
    re.IGNORECASE,
)
_BELITTLE_HINT = re.compile(
    r"(上一个老师|上一任|之前的老师|原来的老师|前任老师|那个老师.*(不行|垃圾|差|坑)|"
    r"老师.*(讲得不好|讲的不好|不行|太差))",
)


class ConductError(Exception):
    """Raised when conduct scan cannot complete."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def heuristic_hints(text: str) -> dict[str, list[str]]:
    """Return short substrings that match common swear / belittle patterns."""
    profanity = sorted({m.group(0) for m in _PROFANITY_HINT.finditer(text)})
    belittle = sorted({m.group(0) for m in _BELITTLE_HINT.finditer(text)})
    return {"profanity_hints": profanity, "belittle_hints": belittle}


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
            raise ConductError("conduct scan response is not valid JSON", EXIT_PIPELINE)
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ConductError(
                f"conduct scan JSON parse failed: {exc}",
                EXIT_PIPELINE,
            ) from exc
    if not isinstance(data, dict):
        raise ConductError("conduct scan JSON must be an object", EXIT_PIPELINE)
    return data


def analyze_conduct(
    corrected_path: Path,
    output_path: Path,
    *,
    title_anchor: str,
    model: str | None = None,
) -> dict[str, Any]:
    """Scan corrected transcript for profanity / belittling prior teachers."""
    if not corrected_path.is_file():
        raise ConductError(f"corrected transcript missing: {corrected_path}", EXIT_USER)
    text = strip_correction_preamble(corrected_path.read_text(encoding="utf-8"))
    if not text.strip():
        raise ConductError(f"corrected transcript empty: {corrected_path}", EXIT_USER)

    hints = heuristic_hints(text)
    user = "\n".join(
        [
            f"title_anchor: {title_anchor}",
            "请按提示词输出言行扫描 JSON（脏话 / 贬低前任讲师）。",
            "必须有摘句；无则 findings 为空。",
            "",
            "## 正则预检提示（仅供参考，不代替摘句判定）",
            json.dumps(hints, ensure_ascii=False),
            "",
            "## 纠错逐字稿",
            text,
        ]
    )
    try:
        system = combine_system_prompts("system_tone", "conduct_scan")
        cfg = load_llm_config(model=model)
        content = chat_completion(system=system, user=user, config=cfg)
        payload = _parse_json_object(content)
    except PromptError as exc:
        raise ConductError(str(exc), EXIT_USER) from exc
    except LLMError as exc:
        raise ConductError(str(exc), exc.exit_code) from exc

    payload.setdefault("schema_version", 1)
    payload.setdefault("title_anchor", title_anchor)
    payload["heuristic_hints"] = hints

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload

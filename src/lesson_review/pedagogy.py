"""Batch pedagogy type: upstream prep docs 004–010 (bypass; not lesson_type)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from lesson_review.checks import EXIT_PIPELINE, EXIT_USER
from lesson_review.llm import LLMError, chat_completion, load_llm_config
from lesson_review.prompts import PromptError, combine_system_prompts
from lesson_review.transcript_text import strip_correction_preamble

PEDAGOGY_TYPES = ("004", "005", "006", "007", "008", "009", "010", "other")
PEDAGOGY_LABELS = {
    "004": "阶段第一课",
    "005": "简介类",
    "006": "实操类",
    "007": "代码语法类",
    "008": "案例类",
    "009": "原理类",
    "010": "项目类",
    "other": "其他（待校准）",
}


class PedagogyTypeError(Exception):
    """Raised when pedagogy type classification cannot complete."""

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
            raise PedagogyTypeError("pedagogy type response is not valid JSON", EXIT_PIPELINE)
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise PedagogyTypeError(
                f"pedagogy type JSON parse failed: {exc}",
                EXIT_PIPELINE,
            ) from exc
    if not isinstance(data, dict):
        raise PedagogyTypeError("pedagogy type JSON must be an object", EXIT_PIPELINE)
    return data


def normalize_pedagogy_type(value: str | None) -> str:
    """Return a valid pedagogy_type code, defaulting to other."""
    if value is None:
        return "other"
    cleaned = value.strip().lower()
    if cleaned in PEDAGOGY_TYPES:
        return cleaned
    # Allow bare numbers like 4 → 004
    if cleaned.isdigit() and len(cleaned) <= 3:
        padded = cleaned.zfill(3)
        if padded in PEDAGOGY_TYPES:
            return padded
    return "other"


def classify_pedagogy_type(
    corrected_path: Path,
    output_path: Path,
    *,
    title_anchor: str,
    model: str | None = None,
) -> dict[str, Any]:
    """Classify upstream prep type 004–010 from corrected transcript."""
    if not corrected_path.is_file():
        raise PedagogyTypeError(f"corrected transcript missing: {corrected_path}", EXIT_USER)
    text = strip_correction_preamble(corrected_path.read_text(encoding="utf-8"))
    if not text.strip():
        raise PedagogyTypeError(f"corrected transcript empty: {corrected_path}", EXIT_USER)

    # Cap prompt size for long lectures; head+tail keeps open/close cues.
    max_chars = 24000
    if len(text) > max_chars:
        head = text[: max_chars // 2]
        tail = text[-(max_chars // 2) :]
        text = head + "\n\n…(中间省略)…\n\n" + tail

    user = "\n".join(
        [
            f"title_anchor: {title_anchor}",
            "请只输出 JSON 对象，字段见系统提示词。",
            "若无法在 004～010 中有把握地单选，pedagogy_type 必须为 other。",
            "",
            "## 纠错逐字稿",
            text,
        ]
    )
    try:
        system = combine_system_prompts("system_tone", "pedagogy_type")
        cfg = load_llm_config(model=model)
        content = chat_completion(system=system, user=user, config=cfg)
        payload = _parse_json_object(content)
    except PromptError as exc:
        raise PedagogyTypeError(str(exc), EXIT_USER) from exc
    except LLMError as exc:
        raise PedagogyTypeError(str(exc), exc.exit_code) from exc

    raw_type = payload.get("pedagogy_type")
    confidence = str(payload.get("confidence") or "").strip().lower()
    pedagogy = normalize_pedagogy_type(str(raw_type) if raw_type is not None else None)
    if confidence == "low" and pedagogy != "other":
        # Conservative: low confidence → other for maintainer calibrate.
        pedagogy = "other"
        payload["downgraded_to_other"] = True

    result = {
        "schema_version": 1,
        "title_anchor": title_anchor,
        "pedagogy_type": pedagogy,
        "pedagogy_type_label": PEDAGOGY_LABELS.get(pedagogy, pedagogy),
        "pedagogy_type_source": "llm",
        "confidence": confidence or "unknown",
        "rationale": str(payload.get("rationale") or "").strip(),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def load_pedagogy_type(path: Path) -> dict[str, Any] | None:
    """Load pedagogy_type.json if present; honor override source."""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    pedagogy = normalize_pedagogy_type(str(data.get("pedagogy_type") or "other"))
    source = str(data.get("pedagogy_type_source") or "llm").strip().lower()
    if source not in {"llm", "override", "other"}:
        source = "llm"
    data["pedagogy_type"] = pedagogy
    data["pedagogy_type_label"] = PEDAGOGY_LABELS.get(pedagogy, pedagogy)
    data["pedagogy_type_source"] = source
    return data

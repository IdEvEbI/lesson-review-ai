"""Pass A knowledge/case review: parse, sanitize gates, and persist JSON."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from lesson_review.checks import EXIT_PIPELINE, EXIT_USER
from lesson_review.llm import LLMError, chat_completion, load_llm_config
from lesson_review.prompts import PromptError, combine_system_prompts
from lesson_review.transcript_text import strip_correction_preamble

SCHEMA_VERSION = 1
VALID_CATEGORIES = {"accuracy", "clarity", "case", "coverage_gap"}
QUALIFYING_CATEGORIES = {"accuracy", "clarity", "case"}
VALID_VERDICTS = {"pass", "issue", "unverified"}
VALID_CONFIDENCE = {"high", "low"}


class KnowledgeError(Exception):
    """Raised when Pass A knowledge review fails."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def infer_anchor_strength(title_anchor: str) -> str:
    """Heuristic: generic day/number titles are weak anchors."""
    stem = title_anchor.strip()
    if len(stem) < 6:
        return "weak"
    if re.fullmatch(r"(?i)day\d+([_-].*)?", stem):
        return "weak"
    if re.fullmatch(r"\d+([._-].*)?", stem) and not re.search(r"[\u4e00-\u9fff]", stem):
        return "weak"
    return "strong"


def extract_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from model output (raw or fenced)."""
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned, flags=re.IGNORECASE)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise KnowledgeError("Pass A did not return a JSON object", EXIT_PIPELINE)
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise KnowledgeError(
                f"Pass A JSON parse failed: {exc}",
                EXIT_PIPELINE,
            ) from exc
    if not isinstance(data, dict):
        raise KnowledgeError("Pass A JSON root must be an object", EXIT_PIPELINE)
    return data


def _evidence_quote(evidence: Any) -> str:
    if evidence is None:
        return ""
    if isinstance(evidence, str):
        return evidence.strip()
    if isinstance(evidence, dict):
        for key in ("quote", "text", "excerpt"):
            value = evidence.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _normalize_evidence(evidence: Any) -> dict[str, str]:
    quote = _evidence_quote(evidence)
    result: dict[str, str] = {"quote": quote}
    if isinstance(evidence, dict):
        approx = evidence.get("approx_time")
        if isinstance(approx, str) and approx.strip():
            result["approx_time"] = approx.strip()
    return result


def sanitize_knowledge_review(
    raw: dict[str, Any],
    *,
    title_anchor: str,
) -> dict[str, Any]:
    """Apply false-positive gates; return a contract-shaped payload."""
    strength = str(raw.get("anchor_strength") or infer_anchor_strength(title_anchor))
    if strength not in {"strong", "weak"}:
        strength = infer_anchor_strength(title_anchor)

    findings_out: list[dict[str, Any]] = []
    raw_findings = raw.get("findings") or []
    if not isinstance(raw_findings, list):
        raw_findings = []

    for index, item in enumerate(raw_findings):
        if not isinstance(item, dict):
            continue
        category = str(item.get("category") or "accuracy").strip()
        if category not in VALID_CATEGORIES:
            category = "accuracy"
        verdict = str(item.get("verdict") or "unverified").strip()
        if verdict not in VALID_VERDICTS:
            verdict = "unverified"
        confidence = str(item.get("confidence") or "low").strip()
        if confidence not in VALID_CONFIDENCE:
            confidence = "low"

        evidence = _normalize_evidence(item.get("evidence"))
        quote = evidence.get("quote", "")

        if category == "coverage_gap":
            verdict = "unverified"
        if verdict == "issue" and not quote:
            verdict = "unverified"
            confidence = "low"
        if strength == "weak" and verdict == "issue" and confidence == "high":
            # Conservative: weak titles cannot emit high-confidence issues.
            confidence = "low"
            verdict = "unverified"

        finding: dict[str, Any] = {
            "id": str(item.get("id") or f"k{index + 1}"),
            "category": category,
            "claim": str(item.get("claim") or "").strip() or "（无说明）",
            "evidence": evidence,
            "verdict": verdict,
            "confidence": confidence,
        }
        remediation = item.get("remediation")
        if isinstance(remediation, str) and remediation.strip():
            finding["remediation"] = remediation.strip()
        elif verdict == "unverified":
            finding["remediation"] = "建议对照讲义或共屏回放确认后再定论。"
        findings_out.append(finding)

    summary = str(raw.get("summary") or "").strip()
    if not summary:
        summary = "专业预审已完成；详见 findings。"

    return {
        "schema_version": SCHEMA_VERSION,
        "title_anchor": title_anchor,
        "anchor_strength": strength,
        "summary": summary,
        "findings": findings_out,
    }


def qualifying_issues(review: dict[str, Any]) -> list[dict[str, Any]]:
    """Findings allowed into 合格线 / Top3 knowledge, clarity, or case slots."""
    result: list[dict[str, Any]] = []
    for item in review.get("findings") or []:
        if not isinstance(item, dict):
            continue
        if item.get("category") not in QUALIFYING_CATEGORIES:
            continue
        if item.get("verdict") != "issue":
            continue
        if item.get("confidence") != "high":
            continue
        if not _evidence_quote(item.get("evidence")):
            continue
        result.append(item)
    return result


def analyze_knowledge(
    corrected_path: Path,
    output_path: Path,
    *,
    title_anchor: str,
    model: str | None = None,
) -> dict[str, Any]:
    """Run Pass A and write sanitized knowledge_review.json. Returns payload."""
    if not corrected_path.is_file():
        raise KnowledgeError(f"corrected transcript missing: {corrected_path}", EXIT_USER)
    corrected = strip_correction_preamble(
        corrected_path.read_text(encoding="utf-8"),
    )
    if not corrected:
        raise KnowledgeError(f"corrected transcript empty: {corrected_path}", EXIT_USER)

    strength_hint = infer_anchor_strength(title_anchor)
    user = "\n".join(
        [
            f"title_anchor: {title_anchor}",
            f"anchor_strength_hint: {strength_hint}",
            "",
            "请输出 knowledge_review JSON（遵守假阳性硬约束；含 clarity 与 summary 禁褒）。",
            "",
            "## 纠错逐字稿",
            corrected,
        ]
    )
    try:
        system = combine_system_prompts("system_tone", "knowledge_cases")
        cfg = load_llm_config(model=model)
        raw_text = chat_completion(system=system, user=user, config=cfg)
        raw_obj = extract_json_object(raw_text)
        payload = sanitize_knowledge_review(raw_obj, title_anchor=title_anchor)
    except PromptError as exc:
        raise KnowledgeError(str(exc), EXIT_USER) from exc
    except LLMError as exc:
        raise KnowledgeError(str(exc), exc.exit_code) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload

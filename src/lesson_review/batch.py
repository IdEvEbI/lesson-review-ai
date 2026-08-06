"""Batch directory: ordered transcribe → correct → conduct scan."""

from __future__ import annotations

import json
import re
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lesson_review.asr import (
    TranscribeError,
    resolve_whisper_language,
    resolve_whisper_model,
    transcribe_audio,
)
from lesson_review.checks import (
    AUDIO_SUFFIXES,
    EXIT_DEPS,
    EXIT_USER,
    VIDEO_SUFFIXES,
    check_llm_api_key,
)
from lesson_review.conduct import ConductError, analyze_conduct
from lesson_review.correct import CorrectError, correct_transcript
from lesson_review.llm import load_llm_config
from lesson_review.media import ExtractAudioError, extract_audio
from lesson_review.pipeline import PipelineError, file_sha256_short, prompt_version_token

_MEDIA_SUFFIXES = VIDEO_SUFFIXES | AUDIO_SUFFIXES
_PREFIX_NUM = re.compile(r"^(\d+)")


@dataclass
class BatchItemResult:
    index: int
    stem: str
    input_path: Path
    item_dir: Path
    status: str
    duration_ms: int | None = None
    finding_count: int = 0
    error: str | None = None


@dataclass
class BatchResult:
    batch_id: str
    batch_dir: Path
    summary_path: Path
    manifest_path: Path
    items: list[BatchItemResult] = field(default_factory=list)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sort_key_media(path: Path) -> tuple[int, str]:
    """Sort by leading numeric prefix, then by name."""
    match = _PREFIX_NUM.match(path.stem)
    if match:
        return (int(match.group(1)), path.name.lower())
    # Files without a leading number go after numbered ones.
    return (10**9, path.name.lower())


def list_media_sorted(directory: Path) -> list[Path]:
    if not directory.is_dir():
        raise PipelineError(f"not a directory: {directory}", EXIT_USER)
    files = [
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in _MEDIA_SUFFIXES
    ]
    return sorted(files, key=sort_key_media)


def _safe_dir_name(stem: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff\-_.]+", "_", stem, flags=re.UNICODE)
    return cleaned[:120] or "item"


def batch_id_from_input_dir(input_dir: Path) -> str:
    """Derive a stable batch folder name from the input directory basename.

    Prefer the human folder name (e.g. a day-of-class label) so outputs are
    easy to find next to ``data/input/<同名>/``. Falls back when the name is
    empty or a filesystem sentinel like ``.``.
    """
    name = _safe_dir_name(input_dir.name.strip() or "")
    if name in {"", ".", "..", "item"}:
        stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
        return f"conduct_{stamp}"
    return name


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _render_summary(batch_id: str, items: list[BatchItemResult], scans: list[dict]) -> str:
    lines = [
        f"# 言行扫描汇总 · `{batch_id}`",
        "",
        "用途：转写 → 纠错 → 高风险话术核查（粗俗辱骂 / 诋毁学科或课程 / 贬低前任讲师）。",
        "对事不对人；以下为摘句证据与建议处置路径汇总（对齐上游 A07 / 薄标准 §5）。",
        "",
        "## 总览",
        "",
        f"- 文件数：{len(items)}",
        f"- 成功：{sum(1 for i in items if i.status == 'ok')}",
        f"- 失败：{sum(1 for i in items if i.status == 'error')}",
        f"- 含 findings 的片段数：{sum(1 for i in items if i.finding_count > 0)}",
        "",
        "## 分文件",
        "",
    ]
    for item, scan in zip(items, scans, strict=False):
        lines.append(f"### {item.index:02d} · {item.stem}")
        lines.append("")
        lines.append(f"- 状态：`{item.status}`")
        lines.append(f"- 目录：`{item.item_dir.name}`")
        if item.error:
            lines.append(f"- 错误：{item.error}")
            lines.append("")
            continue
        summary = ""
        findings: list[Any] = []
        if isinstance(scan, dict):
            summary = str(scan.get("summary") or "").strip()
            raw_findings = scan.get("findings") or []
            if isinstance(raw_findings, list):
                findings = raw_findings
        if summary:
            lines.append(f"- 摘要：{summary}")
        if not findings:
            lines.append("- findings：无")
            lines.append("")
            continue
        lines.append("")
        lines.append("| 类别 | 判断 | 摘句 | 置信 | 建议处置 |")
        lines.append("| ---- | ---- | ---- | ---- | -------- |")
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            cat = str(finding.get("category") or "")
            claim = str(finding.get("claim") or "").replace("|", "\\|")
            evidence = finding.get("evidence") if isinstance(finding.get("evidence"), dict) else {}
            quote = str(evidence.get("quote") or "").replace("|", "\\|").replace("\n", " ")
            conf = str(finding.get("confidence") or "")
            disposition = str(finding.get("disposition_path") or "").replace("|", "\\|")
            lines.append(f"| `{cat}` | {claim} | {quote} | {conf} | `{disposition}` |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def run_batch_conduct(
    input_dir: Path,
    *,
    output_dir: Path = Path("output"),
    language: str | None = None,
    whisper_model: str | None = None,
    llm_model: str | None = None,
    limit: int | None = None,
    force: bool = False,
) -> BatchResult:
    """Process media files in order: extract → ASR → correct → conduct scan."""
    key_check = check_llm_api_key()
    if not key_check.ok:
        raise PipelineError(key_check.detail, EXIT_DEPS)

    media = list_media_sorted(input_dir)
    if not media:
        raise PipelineError(f"no media files in {input_dir}", EXIT_USER)
    if limit is not None:
        if limit < 1:
            raise PipelineError("--limit must be >= 1", EXIT_USER)
        media = media[:limit]

    started = _utc_now()
    batch_id = batch_id_from_input_dir(input_dir)
    batch_dir = output_dir / batch_id
    if batch_dir.exists():
        if not force:
            raise PipelineError(
                f"batch directory already exists: {batch_dir} (use --force)",
                EXIT_USER,
            )
        shutil.rmtree(batch_dir)
    batch_dir.mkdir(parents=True, exist_ok=True)

    asr_model = resolve_whisper_model(whisper_model)
    asr_language = resolve_whisper_language(language)
    llm_model_resolved = load_llm_config(model=llm_model).model

    items: list[BatchItemResult] = []
    scans: list[dict[str, Any]] = []

    for index, path in enumerate(media, start=1):
        t0 = time.perf_counter()
        item_dir = batch_dir / f"{index:02d}_{_safe_dir_name(path.stem)}"
        item_dir.mkdir(parents=True, exist_ok=True)
        (item_dir / "audio").mkdir(parents=True, exist_ok=True)
        raw_path = item_dir / "transcript_raw.json"
        corrected_path = item_dir / "transcript_corrected.md"
        conduct_path = item_dir / "conduct_scan.json"

        try:
            suffix = path.suffix.lower()
            if suffix in VIDEO_SUFFIXES:
                audio_path = item_dir / "audio" / f"{path.stem}.mp3"
                extract_audio(path, audio_path, fmt="mp3")
            elif suffix in AUDIO_SUFFIXES:
                audio_path = item_dir / "audio" / path.name
                shutil.copy2(path, audio_path)
            else:
                raise PipelineError(f"unsupported suffix: {suffix}", EXIT_USER)

            transcribe_audio(
                audio_path,
                raw_path,
                language=asr_language,
                whisper_model=asr_model,
            )
            correct_transcript(
                raw_path,
                corrected_path,
                model=llm_model_resolved,
            )
            payload = analyze_conduct(
                corrected_path,
                conduct_path,
                title_anchor=path.stem,
                model=llm_model_resolved,
            )
            findings = payload.get("findings") if isinstance(payload, dict) else []
            count = len(findings) if isinstance(findings, list) else 0
            items.append(
                BatchItemResult(
                    index=index,
                    stem=path.stem,
                    input_path=path.resolve(),
                    item_dir=item_dir.resolve(),
                    status="ok",
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                    finding_count=count,
                )
            )
            scans.append(payload if isinstance(payload, dict) else {})
        except (
            ExtractAudioError,
            TranscribeError,
            CorrectError,
            ConductError,
            PipelineError,
        ) as exc:
            items.append(
                BatchItemResult(
                    index=index,
                    stem=path.stem,
                    input_path=path.resolve(),
                    item_dir=item_dir.resolve(),
                    status="error",
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                    error=str(exc),
                )
            )
            scans.append({})
            # Continue remaining files; complaint batches should not abort all.
            continue

    summary_path = batch_dir / "summary.md"
    summary_path.write_text(_render_summary(batch_id, items, scans), encoding="utf-8")
    manifest_path = batch_dir / "batch_manifest.json"
    _write_json(
        manifest_path,
        {
            "batch_id": batch_id,
            "mode": "batch_conduct",
            "input_dir": str(input_dir.resolve()),
            "started_at": started.isoformat(),
            "finished_at": _utc_now().isoformat(),
            "asr": {"engine": "mlx_whisper", "model": asr_model},
            "llm": {
                "provider": "openai_compatible",
                "model": llm_model_resolved,
                "prompt_version": prompt_version_token(),
            },
            "items": [
                {
                    "index": item.index,
                    "stem": item.stem,
                    "path": str(item.input_path),
                    "sha256_8": file_sha256_short(item.input_path)
                    if item.input_path.is_file()
                    else None,
                    "item_dir": str(item.item_dir),
                    "status": item.status,
                    "duration_ms": item.duration_ms,
                    "finding_count": item.finding_count,
                    "error": item.error,
                }
                for item in items
            ],
        },
    )
    return BatchResult(
        batch_id=batch_id,
        batch_dir=batch_dir.resolve(),
        summary_path=summary_path.resolve(),
        manifest_path=manifest_path.resolve(),
        items=items,
    )

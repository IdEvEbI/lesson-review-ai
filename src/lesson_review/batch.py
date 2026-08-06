"""Batch directory: ordered transcribe → correct → conduct scan (+ enrichment)."""

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
from lesson_review.media import ExtractAudioError, extract_audio, probe_duration_seconds
from lesson_review.outline import (
    OutlineError,
    analyze_batch_outline,
    format_duration,
    render_outline_markdown,
)
from lesson_review.pedagogy import (
    PEDAGOGY_LABELS,
    PedagogyTypeError,
    classify_pedagogy_type,
    load_pedagogy_type,
)
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
    media_duration_s: float | None = None
    pedagogy_type: str | None = None
    pedagogy_type_source: str | None = None
    finding_count: int = 0
    outline: dict[str, Any] | None = None
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


def duration_from_transcript(raw_path: Path) -> float | None:
    """Fallback duration from ASR segment end times."""
    if not raw_path.is_file():
        return None
    try:
        data = json.loads(raw_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    segments = data.get("segments") if isinstance(data, dict) else None
    if not isinstance(segments, list) or not segments:
        return None
    last = segments[-1]
    if not isinstance(last, dict):
        return None
    end = last.get("end")
    try:
        value = float(end)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def resolve_media_duration(
    media_path: Path,
    *,
    audio_path: Path | None = None,
    transcript_raw: Path | None = None,
) -> float | None:
    """Prefer ffprobe on source/audio; fall back to transcript timestamps."""
    for candidate in (media_path, audio_path):
        if candidate is None:
            continue
        probed = probe_duration_seconds(candidate)
        if probed is not None:
            return probed
    if transcript_raw is not None:
        return duration_from_transcript(transcript_raw)
    return None


def _pedagogy_distribution(items: list[BatchItemResult]) -> list[tuple[str, float, float]]:
    """Return rows of (type, seconds, share) sorted by seconds desc."""
    totals: dict[str, float] = {}
    for item in items:
        if item.status != "ok":
            continue
        key = item.pedagogy_type or "other"
        seconds = item.media_duration_s or 0.0
        totals[key] = totals.get(key, 0.0) + seconds
    grand = sum(totals.values())
    rows = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    out: list[tuple[str, float, float]] = []
    for key, seconds in rows:
        share = (seconds / grand) if grand > 0 else 0.0
        out.append((key, seconds, share))
    return out


def _render_summary(
    batch_id: str,
    items: list[BatchItemResult],
    scans: list[dict],
    *,
    with_outline: bool = False,
) -> str:
    ok_items = [i for i in items if i.status == "ok"]
    total_s = sum(i.media_duration_s or 0.0 for i in ok_items)
    lines = [
        f"# 言行扫描汇总 · `{batch_id}`",
        "",
        "用途：转写 → 纠错 → 高风险话术核查（粗俗辱骂 / 诋毁学科或课程 / 贬低前任讲师）；"
        "并汇总时长与细课型日分布（旁路，非主路径课评）。",
        "对事不对人；细课型不确定时为 `other`，可由维护者校准。",
        "",
        "## 总览",
        "",
        f"- 文件数：{len(items)}",
        f"- 成功：{sum(1 for i in items if i.status == 'ok')}",
        f"- 失败：{sum(1 for i in items if i.status == 'error')}",
        f"- 含 findings 的片段数：{sum(1 for i in items if i.finding_count > 0)}",
        f"- 成功段合计时长：`{format_duration(total_s)}`",
        "",
        "| 序号 | 文件 | 时长 | 细课型 | findings | 状态 |",
        "| ---- | ---- | ---- | ------ | -------- | ---- |",
    ]
    for item in items:
        ped = item.pedagogy_type or "—"
        if item.pedagogy_type:
            label = PEDAGOGY_LABELS.get(item.pedagogy_type, "")
            ped = f"`{item.pedagogy_type}`" + (f" {label}" if label else "")
        lines.append(
            "| {idx:02d} | {stem} | {dur} | {ped} | {find} | `{status}` |".format(
                idx=item.index,
                stem=item.stem.replace("|", "\\|"),
                dur=format_duration(item.media_duration_s),
                ped=ped.replace("|", "\\|"),
                find=item.finding_count if item.status == "ok" else "—",
                status=item.status,
            )
        )

    lines.extend(["", "## 细课型日分布（时长加权）", ""])
    dist = _pedagogy_distribution(items)
    if not dist:
        lines.append("（无成功段，暂无分布）")
        lines.append("")
    else:
        lines.append("| 细课型 | 时长 | 占比 |")
        lines.append("| ------ | ---- | ---- |")
        for key, seconds, share in dist:
            label = PEDAGOGY_LABELS.get(key, "")
            name = f"`{key}`" + (f" {label}" if label else "")
            lines.append(
                f"| {name} | {format_duration(seconds)} | {share * 100:.1f}% |"
            )
        lines.append("")
        lines.append(
            "说明：占比按**成功段媒体时长**合计；`other` 待维护者校准后再解读。"
        )
        lines.append("")

    lines.extend(["## 分文件", ""])
    for item, scan in zip(items, scans, strict=False):
        lines.append(f"### {item.index:02d} · {item.stem}")
        lines.append("")
        lines.append(f"- 状态：`{item.status}`")
        lines.append(f"- 目录：`{item.item_dir.name}`")
        lines.append(f"- 时长：`{format_duration(item.media_duration_s)}`")
        if item.pedagogy_type:
            label = PEDAGOGY_LABELS.get(item.pedagogy_type, "")
            src = item.pedagogy_type_source or "llm"
            lines.append(
                f"- 细课型：`{item.pedagogy_type}`"
                + (f" {label}" if label else "")
                + f"（来源 `{src}`）"
            )
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
        else:
            lines.append("")
            lines.append("| 类别 | 判断 | 摘句 | 置信 | 建议处置 |")
            lines.append("| ---- | ---- | ---- | ---- | -------- |")
            for finding in findings:
                if not isinstance(finding, dict):
                    continue
                cat = str(finding.get("category") or "")
                claim = str(finding.get("claim") or "").replace("|", "\\|")
                evidence = (
                    finding.get("evidence")
                    if isinstance(finding.get("evidence"), dict)
                    else {}
                )
                quote = (
                    str(evidence.get("quote") or "").replace("|", "\\|").replace("\n", " ")
                )
                conf = str(finding.get("confidence") or "")
                disposition = str(finding.get("disposition_path") or "").replace("|", "\\|")
                lines.append(
                    f"| `{cat}` | {claim} | {quote} | {conf} | `{disposition}` |"
                )

        if with_outline and item.outline:
            lines.append("")
            lines.append("#### 讲解结构")
            lines.append("")
            mainline = str(item.outline.get("mainline") or "").strip()
            scatter = str(item.outline.get("scatter_note") or "").strip()
            if mainline:
                lines.append(f"- 主线：{mainline}")
            if scatter:
                lines.append(f"- 散点观察：{scatter}")
            nodes = item.outline.get("nodes") if isinstance(item.outline, dict) else None
            if isinstance(nodes, list) and nodes:
                lines.append("")
                for index, node in enumerate(nodes[:12], start=1):
                    if not isinstance(node, dict):
                        continue
                    title = str(node.get("title") or "").strip() or f"节点 {index}"
                    one = str(node.get("one_liner") or "").strip()
                    start = node.get("start_s")
                    # Ordered list only — never "- 1." (mixed ul/ol breaks Markdown).
                    if isinstance(start, (int, float)):
                        head = f"{index}. `{format_duration(float(start))}` **{title}**"
                    else:
                        head = f"{index}. **{title}**"
                    lines.append(head + (f" — {one}" if one else ""))
            elif not mainline and not scatter:
                lines.append("- （无结构节点）")
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
    with_outline: bool = False,
) -> BatchResult:
    """Process media files in order: extract → ASR → correct → conduct (+ enrichment)."""
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
        pedagogy_path = item_dir / "pedagogy_type.json"
        outline_json = item_dir / "outline.json"
        outline_md = item_dir / "outline.md"
        audio_path: Path | None = None
        outline_payload: dict[str, Any] | None = None

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
            media_duration_s = resolve_media_duration(
                path,
                audio_path=audio_path,
                transcript_raw=raw_path,
            )
            payload = analyze_conduct(
                corrected_path,
                conduct_path,
                title_anchor=path.stem,
                model=llm_model_resolved,
            )
            findings = payload.get("findings") if isinstance(payload, dict) else []
            count = len(findings) if isinstance(findings, list) else 0

            existing_pedagogy = load_pedagogy_type(pedagogy_path)
            if (
                existing_pedagogy
                and existing_pedagogy.get("pedagogy_type_source") == "override"
            ):
                pedagogy = existing_pedagogy
            else:
                pedagogy = classify_pedagogy_type(
                    corrected_path,
                    pedagogy_path,
                    title_anchor=path.stem,
                    model=llm_model_resolved,
                )

            if with_outline:
                outline_payload = analyze_batch_outline(
                    corrected_path,
                    outline_json,
                    outline_md,
                    title_anchor=path.stem,
                    model=llm_model_resolved,
                )

            items.append(
                BatchItemResult(
                    index=index,
                    stem=path.stem,
                    input_path=path.resolve(),
                    item_dir=item_dir.resolve(),
                    status="ok",
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                    media_duration_s=media_duration_s,
                    pedagogy_type=str(pedagogy.get("pedagogy_type") or "other"),
                    pedagogy_type_source=str(
                        pedagogy.get("pedagogy_type_source") or "llm"
                    ),
                    finding_count=count,
                    outline=outline_payload,
                )
            )
            scans.append(payload if isinstance(payload, dict) else {})
        except (
            ExtractAudioError,
            TranscribeError,
            CorrectError,
            ConductError,
            PedagogyTypeError,
            OutlineError,
            PipelineError,
        ) as exc:
            media_duration_s = resolve_media_duration(
                path,
                audio_path=audio_path,
                transcript_raw=raw_path if raw_path.is_file() else None,
            )
            items.append(
                BatchItemResult(
                    index=index,
                    stem=path.stem,
                    input_path=path.resolve(),
                    item_dir=item_dir.resolve(),
                    status="error",
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                    media_duration_s=media_duration_s,
                    error=str(exc),
                )
            )
            scans.append({})
            # Continue remaining files; complaint batches should not abort all.
            continue

    summary_path = batch_dir / "summary.md"
    summary_path.write_text(
        _render_summary(batch_id, items, scans, with_outline=with_outline),
        encoding="utf-8",
    )
    manifest_path = batch_dir / "batch_manifest.json"
    _write_json(
        manifest_path,
        {
            "batch_id": batch_id,
            "mode": "batch_conduct",
            "input_dir": str(input_dir.resolve()),
            "with_outline": with_outline,
            "started_at": started.isoformat(),
            "finished_at": _utc_now().isoformat(),
            "asr": {"engine": "mlx_whisper", "model": asr_model},
            "llm": {
                "provider": "openai_compatible",
                "model": llm_model_resolved,
                "prompt_version": prompt_version_token(),
            },
            "totals": {
                "media_duration_s": sum(
                    (i.media_duration_s or 0.0) for i in items if i.status == "ok"
                ),
                "pedagogy_distribution": [
                    {
                        "pedagogy_type": key,
                        "seconds": seconds,
                        "share": share,
                        "label": PEDAGOGY_LABELS.get(key, key),
                    }
                    for key, seconds, share in _pedagogy_distribution(items)
                ],
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
                    "media_duration_s": item.media_duration_s,
                    "pedagogy_type": item.pedagogy_type,
                    "pedagogy_type_source": item.pedagogy_type_source,
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


def refresh_batch_summary(batch_dir: Path, *, with_outline: bool | None = None) -> Path:
    """Re-render summary.md from existing per-item artifacts (no ASR/LLM).

    Honors ``pedagogy_type.json`` overrides (``pedagogy_type_source=override``).
    """
    if not batch_dir.is_dir():
        raise PipelineError(f"not a directory: {batch_dir}", EXIT_USER)
    manifest_path = batch_dir / "batch_manifest.json"
    if not manifest_path.is_file():
        raise PipelineError(f"missing batch_manifest.json in {batch_dir}", EXIT_USER)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    batch_id = str(manifest.get("batch_id") or batch_dir.name)
    flag_outline = (
        bool(manifest.get("with_outline")) if with_outline is None else with_outline
    )

    items: list[BatchItemResult] = []
    scans: list[dict[str, Any]] = []
    for meta in sorted(manifest.get("items") or [], key=lambda m: m.get("index", 0)):
        if not isinstance(meta, dict):
            continue
        item_dir = Path(str(meta.get("item_dir") or ""))
        stem = str(meta.get("stem") or item_dir.name)
        index = int(meta.get("index") or 0)
        conduct_path = item_dir / "conduct_scan.json"
        pedagogy_path = item_dir / "pedagogy_type.json"
        raw_path = item_dir / "transcript_raw.json"
        outline_json = item_dir / "outline.json"
        input_path = Path(str(meta.get("path") or stem))

        scan: dict[str, Any] = {}
        if conduct_path.is_file():
            try:
                loaded_scan = json.loads(conduct_path.read_text(encoding="utf-8"))
                if isinstance(loaded_scan, dict):
                    scan = loaded_scan
            except json.JSONDecodeError:
                scan = {}

        pedagogy = load_pedagogy_type(pedagogy_path)
        outline_payload = None
        if outline_json.is_file():
            try:
                outline_payload = json.loads(outline_json.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                outline_payload = None
            if isinstance(outline_payload, dict):
                md_path = item_dir / "outline.md"
                md_path.write_text(
                    render_outline_markdown(outline_payload),
                    encoding="utf-8",
                )

        media_duration_s = meta.get("media_duration_s")
        if media_duration_s is None:
            media_duration_s = resolve_media_duration(
                input_path,
                transcript_raw=raw_path if raw_path.is_file() else None,
            )
        else:
            try:
                media_duration_s = float(media_duration_s)
            except (TypeError, ValueError):
                media_duration_s = None

        findings = scan.get("findings") if isinstance(scan.get("findings"), list) else []
        status = str(meta.get("status") or ("ok" if conduct_path.is_file() else "error"))
        items.append(
            BatchItemResult(
                index=index,
                stem=stem,
                input_path=input_path,
                item_dir=item_dir,
                status=status,
                duration_ms=meta.get("duration_ms"),
                media_duration_s=media_duration_s,
                pedagogy_type=(
                    str(pedagogy.get("pedagogy_type")) if pedagogy else meta.get("pedagogy_type")
                ),
                pedagogy_type_source=(
                    str(pedagogy.get("pedagogy_type_source"))
                    if pedagogy
                    else meta.get("pedagogy_type_source")
                ),
                finding_count=len(findings),
                outline=outline_payload if isinstance(outline_payload, dict) else None,
                error=meta.get("error"),
            )
        )
        scans.append(scan)

    summary_path = batch_dir / "summary.md"
    summary_path.write_text(
        _render_summary(batch_id, items, scans, with_outline=flag_outline),
        encoding="utf-8",
    )
    manifest["totals"] = {
        "media_duration_s": sum(
            (i.media_duration_s or 0.0) for i in items if i.status == "ok"
        ),
        "pedagogy_distribution": [
            {
                "pedagogy_type": key,
                "seconds": seconds,
                "share": share,
                "label": PEDAGOGY_LABELS.get(key, key),
            }
            for key, seconds, share in _pedagogy_distribution(items)
        ],
    }
    for meta, item in zip(manifest.get("items") or [], items, strict=False):
        if isinstance(meta, dict):
            meta["media_duration_s"] = item.media_duration_s
            meta["pedagogy_type"] = item.pedagogy_type
            meta["pedagogy_type_source"] = item.pedagogy_type_source
            meta["finding_count"] = item.finding_count
    _write_json(manifest_path, manifest)
    return summary_path.resolve()


def enrich_batch_from_transcripts(
    batch_dir: Path,
    *,
    llm_model: str | None = None,
    with_outline: bool = False,
) -> Path:
    """Backfill duration + pedagogy (+ optional outline) on an existing batch.

    Skips ASR/extract/correct/conduct when artifacts already exist. Useful after
    upgrading summary schema without re-running Whisper.
    """
    if not batch_dir.is_dir():
        raise PipelineError(f"not a directory: {batch_dir}", EXIT_USER)
    manifest_path = batch_dir / "batch_manifest.json"
    if not manifest_path.is_file():
        raise PipelineError(f"missing batch_manifest.json in {batch_dir}", EXIT_USER)

    key_check = check_llm_api_key()
    if not key_check.ok:
        raise PipelineError(key_check.detail, EXIT_DEPS)
    llm_model_resolved = load_llm_config(model=llm_model).model

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for meta in manifest.get("items") or []:
        if not isinstance(meta, dict):
            continue
        item_dir = Path(str(meta.get("item_dir") or ""))
        stem = str(meta.get("stem") or item_dir.name)
        corrected = item_dir / "transcript_corrected.md"
        raw_path = item_dir / "transcript_raw.json"
        pedagogy_path = item_dir / "pedagogy_type.json"
        outline_json = item_dir / "outline.json"
        outline_md = item_dir / "outline.md"
        input_path = Path(str(meta.get("path") or ""))
        audio_candidates = list((item_dir / "audio").glob("*")) if (item_dir / "audio").is_dir() else []
        audio_path = audio_candidates[0] if audio_candidates else None

        media_duration_s = resolve_media_duration(
            input_path if input_path.is_file() else item_dir,
            audio_path=audio_path,
            transcript_raw=raw_path if raw_path.is_file() else None,
        )
        meta["media_duration_s"] = media_duration_s

        if not corrected.is_file():
            continue

        existing = load_pedagogy_type(pedagogy_path)
        if existing and existing.get("pedagogy_type_source") == "override":
            meta["pedagogy_type"] = existing.get("pedagogy_type")
            meta["pedagogy_type_source"] = "override"
        else:
            try:
                pedagogy = classify_pedagogy_type(
                    corrected,
                    pedagogy_path,
                    title_anchor=stem,
                    model=llm_model_resolved,
                )
                meta["pedagogy_type"] = pedagogy.get("pedagogy_type")
                meta["pedagogy_type_source"] = pedagogy.get("pedagogy_type_source")
            except PedagogyTypeError as exc:
                meta["pedagogy_type"] = "other"
                meta["pedagogy_type_source"] = "llm"
                meta["pedagogy_error"] = str(exc)

        if with_outline:
            try:
                analyze_batch_outline(
                    corrected,
                    outline_json,
                    outline_md,
                    title_anchor=stem,
                    model=llm_model_resolved,
                )
            except OutlineError as exc:
                meta["outline_error"] = str(exc)

    manifest["with_outline"] = with_outline or bool(manifest.get("with_outline"))
    _write_json(manifest_path, manifest)
    return refresh_batch_summary(batch_dir, with_outline=manifest["with_outline"])

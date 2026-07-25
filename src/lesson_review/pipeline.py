"""Single-video pipeline orchestration for ``lesson-review run``."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lesson_review.analyze import (
    AnalyzeError,
    analyze_coach,
    analyze_structure,
    analyze_teaching_outline,
)
from lesson_review.asr import (
    TranscribeError,
    resolve_whisper_language,
    resolve_whisper_model,
    transcribe_audio,
)
from lesson_review.checks import (
    AUDIO_SUFFIXES,
    EXIT_DEPS,
    EXIT_PIPELINE,
    EXIT_USER,
    VIDEO_SUFFIXES,
    check_input_path,
    check_llm_api_key,
)
from lesson_review.correct import CorrectError, correct_transcript
from lesson_review.knowledge import KnowledgeError, analyze_knowledge
from lesson_review.lesson_type import (
    LessonTypeError,
    infer_lesson_type,
    parse_lesson_type_cli,
)
from lesson_review.llm import load_llm_config
from lesson_review.media import ExtractAudioError, extract_audio
from lesson_review.report import render_single_report


class PipelineError(Exception):
    """Raised when the single-video pipeline cannot complete."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass
class StepRecord:
    name: str
    status: str = "pending"
    duration_ms: int | None = None
    detail: str | None = None


@dataclass
class PipelineResult:
    run_id: str
    run_dir: Path
    report_path: Path | None
    manifest_path: Path
    steps: list[StepRecord] = field(default_factory=list)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def file_sha256_short(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:8]


def make_run_id(input_path: Path, when: datetime | None = None) -> str:
    stamp = (when or _utc_now()).astimezone().strftime("%Y%m%d-%H%M%S")
    return f"{stamp}_{file_sha256_short(input_path)}"


def prompt_version_token() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode == 0 and completed.stdout.strip():
            return completed.stdout.strip()
    except OSError:
        pass
    return "unknown"


def _mark(
    steps: list[StepRecord],
    name: str,
    status: str,
    started: float,
    detail: str | None = None,
) -> None:
    steps.append(
        StepRecord(
            name=name,
            status=status,
            duration_ms=int((time.perf_counter() - started) * 1000),
            detail=detail,
        )
    )


def _write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_single(
    input_path: Path,
    *,
    output_dir: Path = Path("output"),
    language: str | None = None,
    whisper_model: str | None = None,
    llm_model: str | None = None,
    lesson_type: str | None = None,
    skip_llm: bool = False,
    force: bool = False,
) -> PipelineResult:
    """Run extract → ASR → (optional LLM chain) → report for one media file."""
    input_check = check_input_path(input_path)
    if not input_check.ok:
        raise PipelineError(input_check.detail, EXIT_USER)

    if not skip_llm:
        key_check = check_llm_api_key()
        if not key_check.ok:
            raise PipelineError(key_check.detail, EXIT_DEPS)

    started_at = _utc_now()
    run_id = make_run_id(input_path, started_at)
    run_dir = output_dir / run_id
    if run_dir.exists():
        if not force:
            raise PipelineError(
                f"run directory already exists: {run_dir} (use --force)",
                EXIT_USER,
            )
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "audio").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)

    steps: list[StepRecord] = []
    asr_model = resolve_whisper_model(whisper_model)
    asr_language = resolve_whisper_language(language)
    llm_model_resolved: str | None = None
    if not skip_llm:
        llm_model_resolved = load_llm_config(model=llm_model).model

    title_anchor = input_path.stem
    if lesson_type:
        try:
            lesson_type_resolved = parse_lesson_type_cli(lesson_type)
        except LessonTypeError as exc:
            raise PipelineError(str(exc), EXIT_USER) from exc
        lesson_type_source = "cli"
    else:
        lesson_type_resolved, lesson_type_source = infer_lesson_type(title_anchor)

    audio_path: Path
    raw_path = run_dir / "transcript_raw.json"
    corrected_path = run_dir / "transcript_corrected.md"
    knowledge_path = run_dir / "knowledge_review.json"
    structure_path = run_dir / "structure.md"
    outline_path = run_dir / "teaching_outline.md"
    coach_path = run_dir / "coach.md"
    suggestions_path = run_dir / "suggestions.md"
    report_path = run_dir / "report.md"
    manifest_path = run_dir / "manifest.json"
    report_written: Path | None = None

    suffix = input_path.suffix.lower()
    try:
        # --- extract or stage audio ---
        t0 = time.perf_counter()
        if suffix in VIDEO_SUFFIXES:
            audio_path = run_dir / "audio" / f"{input_path.stem}.mp3"
            extract_audio(input_path, audio_path, fmt="mp3")
            _mark(steps, "extract_audio", "ok", t0, str(audio_path))
        elif suffix in AUDIO_SUFFIXES:
            audio_path = run_dir / "audio" / input_path.name
            shutil.copy2(input_path, audio_path)
            _mark(steps, "extract_audio", "skipped", t0, "input already audio")
        else:
            raise PipelineError(f"unsupported suffix: {suffix}", EXIT_USER)

        # --- transcribe ---
        t0 = time.perf_counter()
        transcribe_audio(
            audio_path,
            raw_path,
            language=asr_language,
            whisper_model=asr_model,
        )
        _mark(steps, "transcribe", "ok", t0, str(raw_path))

        if skip_llm:
            _mark(steps, "correct", "skipped", time.perf_counter(), "skip_llm")
            _mark(steps, "knowledge", "skipped", time.perf_counter(), "skip_llm")
            _mark(steps, "structure", "skipped", time.perf_counter(), "skip_llm")
            _mark(steps, "teaching_outline", "skipped", time.perf_counter(), "skip_llm")
            _mark(steps, "coach", "skipped", time.perf_counter(), "skip_llm")
            _mark(steps, "report", "skipped", time.perf_counter(), "skip_llm")
        else:
            t0 = time.perf_counter()
            correct_transcript(
                raw_path,
                corrected_path,
                model=llm_model_resolved,
            )
            _mark(steps, "correct", "ok", t0, str(corrected_path))

            t0 = time.perf_counter()
            knowledge_payload = analyze_knowledge(
                corrected_path,
                knowledge_path,
                title_anchor=title_anchor,
                model=llm_model_resolved,
            )
            _mark(steps, "knowledge", "ok", t0, str(knowledge_path))

            t0 = time.perf_counter()
            analyze_structure(
                corrected_path,
                structure_path,
                lesson_type=lesson_type_resolved,
                model=llm_model_resolved,
            )
            _mark(steps, "structure", "ok", t0, str(structure_path))

            t0 = time.perf_counter()
            analyze_teaching_outline(
                corrected_path,
                structure_path,
                knowledge_path,
                outline_path,
                title_anchor=title_anchor,
                lesson_type=lesson_type_resolved,
                model=llm_model_resolved,
            )
            _mark(steps, "teaching_outline", "ok", t0, str(outline_path))

            t0 = time.perf_counter()
            analyze_coach(
                corrected_path,
                structure_path,
                knowledge_path,
                coach_path,
                lesson_type=lesson_type_resolved,
                suggestions_path=suggestions_path,
                model=llm_model_resolved,
            )
            _mark(steps, "coach", "ok", t0, str(coach_path))

            t0 = time.perf_counter()
            report_text = render_single_report(
                run_id=run_id,
                input_path=input_path.resolve(),
                title_anchor=title_anchor,
                knowledge_review=knowledge_payload,
                structure_md=structure_path.read_text(encoding="utf-8"),
                coach_md=coach_path.read_text(encoding="utf-8"),
                suggestions_md=suggestions_path.read_text(encoding="utf-8"),
                outline_md=outline_path.read_text(encoding="utf-8"),
                lesson_type=lesson_type_resolved,
                lesson_type_source=lesson_type_source,
                corrected_relpath="transcript_corrected.md",
                knowledge_relpath="knowledge_review.json",
                outline_relpath="teaching_outline.md",
                generated_at=_utc_now(),
            )
            report_path.write_text(report_text, encoding="utf-8")
            report_written = report_path.resolve()
            _mark(steps, "report", "ok", t0, str(report_path))

    except (
        ExtractAudioError,
        TranscribeError,
        CorrectError,
        KnowledgeError,
        AnalyzeError,
    ) as exc:
        _mark(
            steps,
            getattr(exc, "step", type(exc).__name__),
            "error",
            time.perf_counter(),
            str(exc),
        )
        finished = _utc_now()
        _write_manifest(
            manifest_path,
            _manifest_payload(
                run_id=run_id,
                input_path=input_path,
                started_at=started_at,
                finished_at=finished,
                asr_model=asr_model,
                llm_model=llm_model_resolved,
                steps=steps,
                report_path=None,
                skip_llm=skip_llm,
                lesson_type=lesson_type_resolved,
                lesson_type_source=lesson_type_source,
                error=str(exc),
            ),
        )
        raise PipelineError(str(exc), exc.exit_code) from exc
    except PipelineError:
        raise
    except Exception as exc:  # noqa: BLE001
        finished = _utc_now()
        _write_manifest(
            manifest_path,
            _manifest_payload(
                run_id=run_id,
                input_path=input_path,
                started_at=started_at,
                finished_at=finished,
                asr_model=asr_model,
                llm_model=llm_model_resolved,
                steps=steps,
                report_path=None,
                skip_llm=skip_llm,
                lesson_type=lesson_type_resolved,
                lesson_type_source=lesson_type_source,
                error=str(exc),
            ),
        )
        raise PipelineError(f"pipeline failed: {exc}", EXIT_PIPELINE) from exc

    finished_at = _utc_now()
    _write_manifest(
        manifest_path,
        _manifest_payload(
            run_id=run_id,
            input_path=input_path,
            started_at=started_at,
            finished_at=finished_at,
            asr_model=asr_model,
            llm_model=llm_model_resolved,
            steps=steps,
            report_path="report.md" if report_written else None,
            skip_llm=skip_llm,
            lesson_type=lesson_type_resolved,
            lesson_type_source=lesson_type_source,
            error=None,
        ),
    )
    return PipelineResult(
        run_id=run_id,
        run_dir=run_dir.resolve(),
        report_path=report_written,
        manifest_path=manifest_path.resolve(),
        steps=steps,
    )


def _manifest_payload(
    *,
    run_id: str,
    input_path: Path,
    started_at: datetime,
    finished_at: datetime,
    asr_model: str,
    llm_model: str | None,
    steps: list[StepRecord],
    report_path: str | None,
    skip_llm: bool,
    lesson_type: str,
    lesson_type_source: str,
    error: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "run_id": run_id,
        "mode": "single",
        "inputs": [
            {
                "path": str(input_path.resolve()),
                "sha256_8": file_sha256_short(input_path),
            }
        ],
        "started_at": _iso(started_at),
        "finished_at": _iso(finished_at),
        "asr": {"engine": "mlx_whisper", "model": asr_model},
        "llm": {
            "provider": "skipped" if skip_llm else "openai_compatible",
            "model": llm_model,
            "prompt_version": prompt_version_token(),
        },
        "lesson_type": lesson_type,
        "lesson_type_source": lesson_type_source,
        "steps": [
            {
                "name": step.name,
                "status": step.status,
                "duration_ms": step.duration_ms,
                "detail": step.detail,
            }
            for step in steps
        ],
        "report_path": report_path,
    }
    if error:
        payload["error"] = error
    return payload

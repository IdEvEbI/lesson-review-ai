"""CLI entry for lesson-review."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from lesson_review import __version__
from lesson_review.asr import (
    TranscribeError,
    resolve_whisper_language,
    resolve_whisper_model,
    transcribe_audio,
)
from lesson_review.batch import run_batch_conduct
from lesson_review.checks import (
    EXIT_DEPS,
    EXIT_OK,
    EXIT_USER,
    check_input_path,
    check_llm_api_key,
    run_dependency_checks,
)
from lesson_review.config import load_env
from lesson_review.correct import CorrectError, correct_transcript
from lesson_review.media import (
    DEFAULT_AUDIO_FORMAT,
    SUPPORTED_AUDIO_FORMATS,
    ExtractAudioError,
    extract_audio,
)
from lesson_review.pipeline import PipelineError, run_single

app = typer.Typer(
    name="lesson-review",
    help="课评教练流水线：抽轨 → 转写 → 纠错 → 结构 → 建议。",
    add_completion=False,
    no_args_is_help=True,
)


def _print_checks(items: list) -> None:
    for item in items:
        mark = "OK" if item.ok else "MISSING"
        req = "required" if item.required else "optional"
        typer.echo(f"[{mark}] {item.name} ({req}): {item.detail}")


@app.callback()
def main_callback() -> None:
    """Lesson review coach CLI."""
    load_env()


@app.command("version")
def version_cmd() -> None:
    """Print package version."""
    typer.echo(__version__)


@app.command("run")
def run_cmd(
    path: Path = typer.Argument(..., exists=False, help="Video or audio file path"),
    output_dir: Path = typer.Option(
        Path("output"),
        "--output-dir",
        help="Output root directory",
    ),
    language: Optional[str] = typer.Option(
        None,
        "--language",
        help="ASR language hint (default: WHISPER_LANGUAGE or zh)",
    ),
    whisper_model: Optional[str] = typer.Option(
        None,
        "--whisper-model",
        help="mlx-whisper model id (default: WHISPER_MODEL or large-v3-turbo)",
    ),
    llm_model: Optional[str] = typer.Option(
        None,
        "--llm-model",
        help="LLM model id (default from env LLM_MODEL)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Validate dependencies and input only; do not call models",
    ),
    skip_llm: bool = typer.Option(
        False,
        "--skip-llm",
        help="Stop after transcription (no correct / structure / coach / report)",
    ),
    lesson_type: Optional[str] = typer.Option(
        None,
        "--lesson-type",
        help="principle | code | lab（默认按文件名推断）",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing run output directory if present",
    ),
) -> None:
    """Run the lesson-review pipeline on one media file."""
    input_check = check_input_path(path)
    dep_checks = run_dependency_checks()
    all_checks = [input_check, *dep_checks]
    _print_checks(all_checks)

    if not input_check.ok:
        raise typer.Exit(code=EXIT_USER)

    required_failed = [c for c in dep_checks if c.required and not c.ok]
    if required_failed:
        raise typer.Exit(code=EXIT_DEPS)

    if dry_run:
        optional_missing = [c.name for c in dep_checks if not c.required and not c.ok]
        if optional_missing:
            typer.echo(
                "Dry-run OK for required deps. "
                f"Optional not ready: {', '.join(optional_missing)}."
            )
        else:
            typer.echo("Dry-run OK: required and optional dependencies look ready.")
        if not skip_llm and not check_llm_api_key().ok:
            typer.echo(
                "Note: full run (without --skip-llm) requires LLM_API_KEY.",
                err=True,
            )
        raise typer.Exit(code=EXIT_OK)

    try:
        result = run_single(
            path,
            output_dir=output_dir,
            language=language,
            whisper_model=whisper_model,
            llm_model=llm_model,
            lesson_type=lesson_type,
            skip_llm=skip_llm,
            force=force,
        )
    except PipelineError as exc:
        typer.echo(f"run failed: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc

    typer.echo(f"run_id: {result.run_id}")
    typer.echo(f"run_dir: {result.run_dir}")
    typer.echo(f"manifest: {result.manifest_path}")
    if result.report_path:
        typer.echo(f"report: {result.report_path}")
    else:
        typer.echo("report: (skipped; use without --skip-llm for full report)")
    raise typer.Exit(code=EXIT_OK)


@app.command("batch-conduct")
def batch_conduct_cmd(
    directory: Path = typer.Argument(
        ...,
        exists=False,
        help="Directory of videos/audio; processed in numeric filename order",
    ),
    output_dir: Path = typer.Option(
        Path("output"),
        "--output-dir",
        help="Output root (writes output/<input-dir-name>/)",
    ),
    language: Optional[str] = typer.Option(
        None,
        "--language",
        help="ASR language hint (default: WHISPER_LANGUAGE or zh)",
    ),
    whisper_model: Optional[str] = typer.Option(
        None,
        "--whisper-model",
        help="mlx-whisper model id",
    ),
    llm_model: Optional[str] = typer.Option(
        None,
        "--llm-model",
        help="LLM model id (default from env LLM_MODEL)",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="Only process the first N files (after sort); for smoke tests",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing batch output directory if present",
    ),
) -> None:
    """Batch: extract → ASR → correct → scan for swearing / belittling prior teachers."""
    if not directory.is_dir():
        typer.echo(f"batch-conduct failed: not a directory: {directory}", err=True)
        raise typer.Exit(code=EXIT_USER)

    dep_checks = run_dependency_checks()
    _print_checks(dep_checks)
    required_failed = [c for c in dep_checks if c.required and not c.ok]
    if required_failed:
        raise typer.Exit(code=EXIT_DEPS)

    try:
        result = run_batch_conduct(
            directory,
            output_dir=output_dir,
            language=language,
            whisper_model=whisper_model,
            llm_model=llm_model,
            limit=limit,
            force=force,
        )
    except PipelineError as exc:
        typer.echo(f"batch-conduct failed: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc

    typer.echo(f"batch_id: {result.batch_id}")
    typer.echo(f"batch_dir: {result.batch_dir}")
    typer.echo(f"summary: {result.summary_path}")
    typer.echo(f"manifest: {result.manifest_path}")
    ok = sum(1 for item in result.items if item.status == "ok")
    err = sum(1 for item in result.items if item.status == "error")
    hits = sum(1 for item in result.items if item.finding_count > 0)
    typer.echo(f"items: {len(result.items)} ok={ok} error={err} with_findings={hits}")
    raise typer.Exit(code=EXIT_OK)


@app.command("check")
def check_cmd() -> None:
    """Print dependency status without requiring an input file."""
    checks = run_dependency_checks()
    _print_checks(checks)
    if any(c.required and not c.ok for c in checks):
        raise typer.Exit(code=EXIT_DEPS)
    raise typer.Exit(code=EXIT_OK)


@app.command("extract-audio")
def extract_audio_cmd(
    path: Path = typer.Argument(..., exists=False, help="Video (or audio) file path"),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output audio path (default: output/<stem>/audio/<stem>.<format>)",
    ),
    fmt: str = typer.Option(
        DEFAULT_AUDIO_FORMAT,
        "--format",
        help=f"Audio format: {', '.join(SUPPORTED_AUDIO_FORMATS)} (default: mp3)",
    ),
    output_dir: Path = typer.Option(
        Path("output"),
        "--output-dir",
        help="Root used when -o is omitted",
    ),
) -> None:
    """Extract mono audio from a media file via ffmpeg (no LLM)."""
    try:
        dest = extract_audio(path, output, fmt, output_root=output_dir)
    except ExtractAudioError as exc:
        typer.echo(f"extract-audio failed: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc

    typer.echo(str(dest))
    raise typer.Exit(code=EXIT_OK)


@app.command("transcribe")
def transcribe_cmd(
    path: Path = typer.Argument(..., exists=False, help="Audio file path"),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output JSON path (default: output/<stem>/transcript_raw.json)",
    ),
    language: Optional[str] = typer.Option(
        None,
        "--language",
        help="ASR language hint (default: WHISPER_LANGUAGE or zh)",
    ),
    whisper_model: Optional[str] = typer.Option(
        None,
        "--whisper-model",
        help="mlx-whisper model id (default: WHISPER_MODEL or large-v3-turbo)",
    ),
    output_dir: Path = typer.Option(
        Path("output"),
        "--output-dir",
        help="Root used when -o is omitted",
    ),
) -> None:
    """Transcribe audio with local mlx-whisper (no LLM)."""
    model = resolve_whisper_model(whisper_model)
    lang = resolve_whisper_language(language)
    try:
        dest = transcribe_audio(
            path,
            output,
            language=lang,
            whisper_model=model,
            output_root=output_dir,
        )
    except TranscribeError as exc:
        typer.echo(f"transcribe failed: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc

    typer.echo(str(dest))
    raise typer.Exit(code=EXIT_OK)


@app.command("correct")
def correct_cmd(
    path: Path = typer.Argument(
        ...,
        exists=False,
        help="transcript_raw.json or .md/.txt transcript path",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path (default: output/<stem>/transcript_corrected.md)",
    ),
    llm_model: Optional[str] = typer.Option(
        None,
        "--llm-model",
        help="LLM model id (default: LLM_MODEL or deepseek-v4-flash)",
    ),
    output_dir: Path = typer.Option(
        Path("output"),
        "--output-dir",
        help="Root used when -o is omitted",
    ),
) -> None:
    """Correct ASR transcript with LLM (requires LLM_API_KEY)."""
    try:
        dest = correct_transcript(
            path,
            output,
            model=llm_model,
            output_root=output_dir,
        )
    except CorrectError as exc:
        typer.echo(f"correct failed: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc

    typer.echo(str(dest))
    raise typer.Exit(code=EXIT_OK)


def run() -> None:
    """Console script fallback."""
    app()


if __name__ == "__main__":
    app()

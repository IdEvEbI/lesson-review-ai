"""ASR correction step via LLM prompts."""

from __future__ import annotations

import json
from pathlib import Path

from lesson_review.checks import EXIT_USER
from lesson_review.llm import LLMError, chat_completion, load_llm_config
from lesson_review.prompts import PromptError, combine_system_prompts


class CorrectError(Exception):
    """Raised when the correct step cannot complete."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def default_corrected_output_path(
    input_path: Path,
    output_root: Path = Path("output"),
) -> Path:
    """Return ``output/<stem>/transcript_corrected.md``."""
    stem = input_path.stem
    if stem == "transcript_raw":
        stem = input_path.parent.name
    return output_root / stem / "transcript_corrected.md"


def load_transcript_text(path: Path) -> str:
    """Load plain text or transcript_raw.json into a user payload string."""
    if not path.exists() or not path.is_file():
        raise CorrectError(f"path does not exist or is not a file: {path}", EXIT_USER)

    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CorrectError(f"invalid JSON transcript: {exc}", EXIT_USER) from exc
        if not isinstance(data, dict):
            raise CorrectError("transcript JSON must be an object", EXIT_USER)
        text = str(data.get("text", "")).strip()
        if not text:
            raise CorrectError("transcript JSON missing non-empty 'text'", EXIT_USER)
        segments = data.get("segments") or []
        lines = [
            "请对下列课堂转写进行纠错与补标点。",
            "",
            "## 全文",
            text,
        ]
        if isinstance(segments, list) and segments:
            lines.extend(["", "## 片段时间（节选，供断句参考）"])
            for segment in segments[:80]:
                if not isinstance(segment, dict):
                    continue
                start = segment.get("start", "?")
                end = segment.get("end", "?")
                seg_text = str(segment.get("text", "")).strip()
                if seg_text:
                    lines.append(f"- [{start}–{end}] {seg_text}")
            if len(segments) > 80:
                lines.append(f"- … 另有 {len(segments) - 80} 个片段未列出")
        return "\n".join(lines)

    if suffix in {".md", ".txt"}:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            raise CorrectError(f"transcript file empty: {path}", EXIT_USER)
        return "请对下列课堂转写进行纠错与补标点。\n\n" + text

    raise CorrectError(
        f"unsupported transcript suffix {suffix!r}; expected .json / .md / .txt",
        EXIT_USER,
    )


def correct_transcript(
    input_path: Path,
    output_path: Path | None = None,
    *,
    model: str | None = None,
    output_root: Path = Path("output"),
) -> Path:
    """Run asr_correct via LLM and write transcript_corrected.md."""
    try:
        user_payload = load_transcript_text(input_path)
        system = combine_system_prompts("system_tone", "asr_correct")
        cfg = load_llm_config(model=model)
    except PromptError as exc:
        raise CorrectError(str(exc), EXIT_USER) from exc
    except LLMError as exc:
        raise CorrectError(str(exc), exc.exit_code) from exc
    except CorrectError:
        raise

    try:
        content = chat_completion(system=system, user=user_payload, config=cfg)
    except LLMError as exc:
        raise CorrectError(str(exc), exc.exit_code) from exc

    dest = output_path or default_corrected_output_path(input_path, output_root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    body = content if content.endswith("\n") else content + "\n"
    dest.write_text(body, encoding="utf-8")
    return dest.resolve()

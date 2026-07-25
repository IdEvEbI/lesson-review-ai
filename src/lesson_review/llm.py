"""OpenAI-compatible LLM client (DeepSeek by default)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from lesson_review.checks import EXIT_DEPS, EXIT_PIPELINE
from lesson_review.config import getenv

logger = logging.getLogger(__name__)

DEFAULT_LLM_BASE_URL = "https://api.deepseek.com"
DEFAULT_LLM_MODEL = "deepseek-v4-flash"
DEFAULT_TIMEOUT_S = 120.0
DEFAULT_MAX_RETRIES = 3
RETRY_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class LLMError(Exception):
    """Raised when the LLM client cannot complete a request."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    timeout_s: float = DEFAULT_TIMEOUT_S
    max_retries: int = DEFAULT_MAX_RETRIES


def _redact_secrets(text: str, api_key: str) -> str:
    if api_key and api_key in text:
        return text.replace(api_key, "***")
    return text


def load_llm_config(
    *,
    model: str | None = None,
    base_url: str | None = None,
) -> LLMConfig:
    api_key = getenv("LLM_API_KEY")
    if not api_key:
        raise LLMError(
            "LLM_API_KEY missing (copy .env.example → .env and set the key)",
            EXIT_DEPS,
        )
    resolved_base = (
        base_url
        or getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL)
        or DEFAULT_LLM_BASE_URL
    )
    resolved_model = model or getenv("LLM_MODEL", DEFAULT_LLM_MODEL) or DEFAULT_LLM_MODEL
    return LLMConfig(api_key=api_key, base_url=resolved_base, model=resolved_model)


def chat_completion(
    *,
    system: str,
    user: str,
    config: LLMConfig | None = None,
    model: str | None = None,
) -> str:
    """Call chat.completions and return assistant text.

    Retries on timeout and selected HTTP status codes (including 429).
    Never logs the API key.
    """
    cfg = config or load_llm_config(model=model)
    if model:
        cfg = LLMConfig(
            api_key=cfg.api_key,
            base_url=cfg.base_url,
            model=model,
            timeout_s=cfg.timeout_s,
            max_retries=cfg.max_retries,
        )

    try:
        from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
    except ImportError as exc:
        raise LLMError(
            "openai package not installed (uv sync)",
            EXIT_DEPS,
        ) from exc

    client = OpenAI(
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        timeout=cfg.timeout_s,
    )

    last_error: Exception | None = None
    for attempt in range(1, cfg.max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=cfg.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            choice = response.choices[0].message.content
            if choice is None or not str(choice).strip():
                raise LLMError("LLM returned empty content", EXIT_PIPELINE)
            return str(choice).strip()
        except LLMError:
            raise
        except APITimeoutError as exc:
            last_error = exc
            logger.warning(
                "LLM timeout on attempt %s/%s",
                attempt,
                cfg.max_retries,
            )
        except APIConnectionError as exc:
            last_error = exc
            logger.warning(
                "LLM connection error on attempt %s/%s: %s",
                attempt,
                cfg.max_retries,
                _redact_secrets(str(exc), cfg.api_key),
            )
        except APIStatusError as exc:
            last_error = exc
            status = getattr(exc, "status_code", None)
            logger.warning(
                "LLM HTTP %s on attempt %s/%s",
                status,
                attempt,
                cfg.max_retries,
            )
            if status not in RETRY_STATUS_CODES:
                raise LLMError(
                    _redact_secrets(f"LLM request failed: {exc}", cfg.api_key),
                    EXIT_PIPELINE,
                ) from exc
        except Exception as exc:  # noqa: BLE001
            raise LLMError(
                _redact_secrets(f"LLM request failed: {exc}", cfg.api_key),
                EXIT_PIPELINE,
            ) from exc

        if attempt < cfg.max_retries:
            time.sleep(min(2 ** (attempt - 1), 8))

    raise LLMError(
        _redact_secrets(
            f"LLM failed after {cfg.max_retries} attempts: {last_error}",
            cfg.api_key,
        ),
        EXIT_PIPELINE,
    )

import io
import json
import logging
import re
import time

from google import genai
from google.genai import types
from groq import Groq

import config

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-1.5-flash"
GROQ_MODEL = "llama-3.1-8b-instant"
JSON_RETRY_ATTEMPTS = 2

_gemini_client = None
_groq_client = None

# Circuit breaker: providers added here are skipped for the rest of the process.
# Triggered by a daily quota 429 — no point retrying until tomorrow.
_exhausted_providers: set[str] = set()


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _gemini_client


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=config.GROQ_API_KEY)
    return _groq_client


def _call_gemini(prompt: str) -> str:
    client = _get_gemini_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return response.text


def _call_groq(prompt: str) -> str:
    client = _get_groq_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


def _call_gemini_vision(prompt: str, image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    client = _get_gemini_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            prompt,
            types.Part.from_bytes(data=buffer.getvalue(), mime_type="image/png"),
        ],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return response.text


PROVIDER_CALLERS = {
    "gemini": _call_gemini,
    "groq": _call_groq,
}

PROVIDER_CHAIN = ["gemini", "groq"]


def _parse_with_retry(call_fn, prompt: str) -> dict | None:
    for attempt in range(1, JSON_RETRY_ATTEMPTS + 1):
        raw = call_fn(prompt)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Malformed JSON on attempt %d/%d: %r", attempt, JSON_RETRY_ATTEMPTS, raw[:200])
    return None


_TRANSIENT_RETRY_ATTEMPTS     = 4
_TRANSIENT_RETRY_FALLBACK_DELAY = 65  # used only if the error message has no delay hint


def _is_daily_quota_error(e: Exception) -> bool:
    msg = str(e)
    return "429" in msg and ("per_day" in msg.lower() or "per day" in msg.lower() or "GenerateRequestsPerDay" in msg)


def _is_transient_rate_limit(e: Exception) -> bool:
    """TPM or RPM limit — temporary, resets within seconds."""
    msg = str(e)
    return "429" in msg and not _is_daily_quota_error(e)


def _parse_retry_delay(e: Exception) -> float:
    """
    Return how long to wait before retrying a rate limit error.
    For token-per-minute (TPM) limits the suggested retry time is misleading —
    the rolling 1-minute window won't clear in a few seconds, so we always
    wait the full minute. For request-per-minute (RPM) limits the suggested
    delay is accurate.
    """
    msg = str(e)
    if "tokens per minute" in msg.lower() or '"type": "tokens"' in msg or "'type': 'tokens'" in msg:
        return 65.0  # wait for the full 1-minute TPM window to reset
    match = re.search(r"try again in (\d+(?:\.\d+)?)\s*s", msg, re.IGNORECASE)
    return float(match.group(1)) + 2 if match else _TRANSIENT_RETRY_FALLBACK_DELAY


def _call_with_transient_retry(call_fn, prompt: str) -> str:
    """Call an LLM function, retrying on transient rate limits using the suggested delay."""
    for attempt in range(1, _TRANSIENT_RETRY_ATTEMPTS + 1):
        try:
            return call_fn(prompt)
        except Exception as e:
            if _is_transient_rate_limit(e) and attempt < _TRANSIENT_RETRY_ATTEMPTS:
                delay = _parse_retry_delay(e)
                logger.warning("transient rate limit (attempt %d/%d), retrying in %.0fs",
                               attempt, _TRANSIENT_RETRY_ATTEMPTS, delay)
                time.sleep(delay)
            else:
                raise


def grade_answer(prompt: str) -> dict:
    start = PROVIDER_CHAIN.index(config.LLM_PROVIDER)

    for provider_name in PROVIDER_CHAIN[start:]:
        if provider_name in _exhausted_providers:
            continue

        call_fn = PROVIDER_CALLERS[provider_name]
        try:
            result = _parse_with_retry(lambda p: _call_with_transient_retry(call_fn, p), prompt)
        except Exception as e:
            if _is_daily_quota_error(e):
                _exhausted_providers.add(provider_name)
                logger.warning("%s daily quota exhausted — switching permanently to next provider", provider_name)
            else:
                logger.warning("%s provider failed (%s), falling back", provider_name, e)
            continue

        if result is not None:
            return result

        logger.warning("%s returned malformed JSON twice, falling back", provider_name)

    raise RuntimeError("All LLM providers failed")


def grade_answer_with_image(prompt: str, image) -> dict | None:
    try:
        return _parse_with_retry(lambda p: _call_gemini_vision(p, image), prompt)
    except Exception as e:
        logger.warning("gemini vision failed (%s), falling back to text grading", e)
        return None

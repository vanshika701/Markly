import io
import json
import logging

from google import genai
from google.genai import types
from groq import Groq

import config

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"
GROQ_MODEL = "llama-3.1-8b-instant"
JSON_RETRY_ATTEMPTS = 2

_gemini_client = None
_groq_client = None


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


def grade_answer(prompt: str) -> dict:
    start = PROVIDER_CHAIN.index(config.LLM_PROVIDER)

    for provider_name in PROVIDER_CHAIN[start:]:
        call_fn = PROVIDER_CALLERS[provider_name]
        try:
            result = _parse_with_retry(call_fn, prompt)
        except Exception as e:
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

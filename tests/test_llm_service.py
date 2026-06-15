import logging
from unittest.mock import MagicMock, patch

import config
import services.llm_service as llm_service
from services.llm_service import grade_answer

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

WATER_CYCLE_PROMPT = """You are grading a student's written answer.

Question: Explain the water cycle.
Reference answer: The water cycle involves evaporation, condensation, and precipitation.
Rubric: Award 3 marks for evaporation, 3 for condensation, 4 for precipitation. Total marks: 10.
Student's answer: Water heats up and evapration happens, then clouds form due to gravity and water falls as rain.

Return ONLY JSON in this exact shape:
{
  "score": <int>,
  "max_score": <int>,
  "feedback": "<string>",
  "confidence": <float 0-1>,
  "spelling_mistakes": [<strings>],
  "correct_parts": [<strings>],
  "wrong_parts": [<strings>]
}
"""

EXPECTED_KEYS = {"score", "max_score", "feedback", "confidence", "spelling_mistakes", "correct_parts", "wrong_parts"}

print("--- 1. real call (happy path) ---")
result = grade_answer(WATER_CYCLE_PROMPT)
print(result)
assert EXPECTED_KEYS.issubset(result.keys())
print("schema OK\n")

print("--- 2. retry recovers (1st call malformed, 2nd valid) ---")
mock_gemini = MagicMock(side_effect=["not json", '{"score": 5, "max_score": 10, "feedback": "ok"}'])
with patch.dict("services.llm_service.PROVIDER_CALLERS", {"gemini": mock_gemini}):
    result = grade_answer("dummy prompt")
    print(result)
    assert result["score"] == 5
    assert mock_gemini.call_count == 2
print("retry-recovers OK\n")

print("--- 3. gemini AND groq both malformed twice -> raises ---")
mock_gemini = MagicMock(return_value="still not json")
mock_groq = MagicMock(return_value="also not json")
with patch.dict("services.llm_service.PROVIDER_CALLERS", {"gemini": mock_gemini, "groq": mock_groq}):
    try:
        grade_answer("dummy prompt")
        print("ERROR: should have raised")
    except RuntimeError as e:
        print(f"raised as expected: {e}")
    assert mock_gemini.call_count == 2
    assert mock_groq.call_count == 2
print("retry-exhausted OK\n")

print("--- 4. fallback chain: gemini fails -> groq answers (real APIs) ---")
original_key = config.GEMINI_API_KEY
config.GEMINI_API_KEY = "invalid_key"
llm_service._gemini_client = None  # drop cached client so the bad key takes effect
try:
    result = grade_answer(WATER_CYCLE_PROMPT)
    print(result)
    assert EXPECTED_KEYS.issubset(result.keys())
    print("fallback to groq OK")
finally:
    config.GEMINI_API_KEY = original_key
    llm_service._gemini_client = None

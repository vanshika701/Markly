from rapidfuzz import fuzz

from services.llm_service import grade_answer
from utils.text_utils import normalize_mcq_answer

MCQ_MATCH_THRESHOLD = 80


def grade_mcq(student_answer: str, answer_key_entry: dict) -> dict:
    marks = answer_key_entry["marks"]
    correct_answer = answer_key_entry["answer"]

    student = normalize_mcq_answer(student_answer)
    correct = normalize_mcq_answer(correct_answer)

    if not student:
        return {"score": 0, "max_score": marks, "feedback": "No answer provided"}

    similarity = fuzz.ratio(student, correct)

    if similarity >= MCQ_MATCH_THRESHOLD:
        return {"score": marks, "max_score": marks, "feedback": "Correct"}

    return {"score": 0, "max_score": marks, "feedback": f"Incorrect — answer was {correct_answer}"}


def _build_written_prompt(student_answer: str, answer_key_entry: dict) -> str:
    return f"""You are grading a student's written answer.

Reference answer: {answer_key_entry["answer"]}
Rubric: {answer_key_entry["rubric"]}
Total marks: {answer_key_entry["marks"]}

Award marks according to the rubric for each concept that is correctly explained.
Deduct marks for incorrect or contradictory statements, even if the required
concepts are also present elsewhere in the answer.

Student's answer: {student_answer}

Return ONLY JSON in this exact shape:
{{
  "score": <int>,
  "max_score": <int>,
  "feedback": "<string>",
  "confidence": <float 0-1>,
  "spelling_mistakes": [<strings>],
  "correct_parts": [<strings>],
  "wrong_parts": [<strings>]
}}
"""


def grade_written(student_answer: str, answer_key_entry: dict) -> dict:
    marks = answer_key_entry["marks"]

    if not student_answer.strip():
        return {
            "score": 0,
            "max_score": marks,
            "feedback": "No answer provided",
            "confidence": 1.0,
            "spelling_mistakes": [],
            "correct_parts": [],
            "wrong_parts": [],
        }

    prompt = _build_written_prompt(student_answer, answer_key_entry)
    result = grade_answer(prompt)

    # answer_key_entry["marks"] is the source of truth — never trust the LLM's echo of max_score.
    result["max_score"] = marks
    result["score"] = max(0, min(int(result.get("score", 0)), marks))

    return result

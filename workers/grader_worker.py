from rapidfuzz import fuzz

from services.llm_service import grade_answer, grade_answer_with_image
from utils.text_utils import normalize_mcq_answer

MCQ_MATCH_THRESHOLD = 80

_GRADING_JSON_SCHEMA = """\
Return ONLY JSON in this exact shape:
{
  "score": <int>,
  "max_score": <int>,
  "feedback": "<string>",
  "confidence": <float 0-1>,
  "spelling_mistakes": [<strings>],
  "correct_parts": [<strings>],
  "wrong_parts": [<strings>]
}"""


def _empty_answer_result(marks: int) -> dict:
    return {
        "score": 0,
        "max_score": marks,
        "feedback": "No answer provided",
        "confidence": 1.0,
        "spelling_mistakes": [],
        "correct_parts": [],
        "wrong_parts": [],
    }


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
    body = (
        "You are grading a student's written answer.\n\n"
        f"Reference answer: {answer_key_entry['answer']}\n"
        f"Rubric: {answer_key_entry['rubric']}\n"
        f"Total marks: {answer_key_entry['marks']}\n\n"
        "Grading rules:\n"
        "1. Use the rubric as a guide for what a strong answer looks like. Award marks when\n"
        "   the student demonstrates the same underlying concept, even if worded differently.\n"
        "   Do NOT award marks if the answer is entirely off-topic or contradicts the rubric.\n"
        "2. Award proportional marks for partially correct answers — not all rubric points\n"
        "   need to be present for partial credit.\n"
        f"3. Award scores in multiples of {answer_key_entry.get('score_step', 1)} only\n"
        f"   (e.g. valid scores: {', '.join(str(round(i * answer_key_entry.get('score_step', 1), 2)) for i in range(int(answer_key_entry['marks'] / answer_key_entry.get('score_step', 1)) + 1))}).\n"
        "4. Deduct marks for incorrect or contradictory statements.\n"
        "5. If the answer does not address the question at all, the score must be 0.\n\n"
        f"Student's answer: {student_answer}\n"
    )
    return body + "\n" + _GRADING_JSON_SCHEMA


def grade_written(student_answer: str, answer_key_entry: dict) -> dict:
    marks = answer_key_entry["marks"]

    if not student_answer.strip():
        return _empty_answer_result(marks)

    prompt = _build_written_prompt(student_answer, answer_key_entry)
    result = grade_answer(prompt)

    # answer_key_entry["marks"] is the source of truth — never trust the LLM's echo of max_score.
    result["max_score"] = marks
    raw = float(result.get("score", 0))
    # Round to nearest 0.5, then clamp to [0, marks]
    result["score"] = max(0.0, min(round(raw * 2) / 2, marks))

    return result


def _build_written_image_prompt(answer_key_entry: dict) -> str:
    body = (
        "You are grading a student's handwritten answer shown in the image.\n\n"
        f"Reference answer: {answer_key_entry['answer']}\n"
        f"Rubric: {answer_key_entry['rubric']}\n"
        f"Total marks: {answer_key_entry['marks']}\n\n"
        "Grading rules:\n"
        "1. Use the rubric as a guide. Award marks when the student demonstrates the same\n"
        "   underlying concept, even if worded differently. Do NOT award marks if the answer\n"
        "   is entirely off-topic or contradicts the rubric.\n"
        "2. Award proportional marks for partially correct answers.\n"
        "3. Scores may be in 0.5 increments (e.g. 1.5, 2.5).\n"
        "4. Deduct marks for incorrect or contradictory statements.\n"
        "5. If the answer does not address the question at all, the score must be 0.\n"
        "Read the handwriting from the image carefully. Capture spelling mistakes exactly\n"
        "as the student wrote them.\n"
    )
    return body + "\n" + _GRADING_JSON_SCHEMA


def grade_written_handwritten(image, ocr_text: str, answer_key_entry: dict) -> dict:
    marks = answer_key_entry["marks"]

    if not ocr_text.strip():
        return _empty_answer_result(marks)

    prompt = _build_written_image_prompt(answer_key_entry)
    result = grade_answer_with_image(prompt, image)

    if result is None:
        # Gemini vision failed — fall back to text-based grading using Tesseract OCR text.
        return grade_written(ocr_text, answer_key_entry)

    result["max_score"] = marks
    raw = float(result.get("score", 0))
    result["score"] = max(0.0, min(round(raw * 2) / 2, marks))
    return result

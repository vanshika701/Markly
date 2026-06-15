from rapidfuzz import fuzz

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

import logging
from unittest.mock import patch

from utils.pdf_utils import convert_pdf_to_images
from workers.grader_worker import grade_written_handwritten

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

PDF_PATH = "samples/handwritten.pdf"

answer_key_entry = {
    "type": "written",
    "answer": "The water cycle involves evaporation, condensation, and precipitation.",
    "rubric": "Award 3 marks for evaporation, 3 for condensation, 4 for precipitation",
    "marks": 10,
}

EXPECTED_KEYS = {
    "score", "max_score", "feedback", "confidence",
    "spelling_mistakes", "correct_parts", "wrong_parts",
}

images = convert_pdf_to_images(PDF_PATH)
page_image = images[0]

print("--- 1. gemini vision reads handwritten PDF ---")
result = grade_written_handwritten(page_image, "placeholder ocr text", answer_key_entry)
print(result)
assert EXPECTED_KEYS.issubset(result.keys())
assert 0 <= result["score"] <= result["max_score"] == answer_key_entry["marks"]
print("vision path OK\n")

print("--- 2. gemini vision fails -> falls back to text grading ---")
with patch("workers.grader_worker.grade_answer_with_image", return_value=None):
    result = grade_written_handwritten(page_image, "Water evaporates and condenses.", answer_key_entry)
    print(result)
    assert EXPECTED_KEYS.issubset(result.keys())
    assert 0 <= result["score"] <= result["max_score"] == answer_key_entry["marks"]
print("fallback path OK\n")

print("--- 3. blank OCR text -> instant zero, no API call ---")
result = grade_written_handwritten(page_image, "   ", answer_key_entry)
print(result)
assert result["score"] == 0
assert result["feedback"] == "No answer provided"
print("blank path OK")

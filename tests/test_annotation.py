import os

from utils.text_utils import build_annotation_map
from workers.annotator_worker import annotate_pdf

PDF_PATH = "samples/handwritten.pdf"
OUTPUT_PATH = "samples/annotated_test.pdf"

# dpi=72 means scale factor = 1.0, so these coordinates are already in PDF points.
# At 72 dpi, 1 unit = 1 PDF point = 1/72 inch, which places annotations at
# readable positions on a standard A4/letter page (e.g. top=150 ≈ 2 inches from top).
DPI = 72

word_map = [
    {"text": "evapration", "left": 100, "top": 150, "width": 80, "height": 20, "conf": 71},
    {"text": "clouds",     "left": 100, "top": 185, "width": 58, "height": 20, "conf": 85},
    {"text": "form",       "left": 165, "top": 185, "width": 40, "height": 20, "conf": 87},
    {"text": "due",        "left": 212, "top": 185, "width": 30, "height": 20, "conf": 89},
    {"text": "to",         "left": 248, "top": 185, "width": 18, "height": 20, "conf": 91},
    {"text": "gravity",    "left": 272, "top": 185, "width": 58, "height": 20, "conf": 83},
    {"text": "Water",      "left": 100, "top": 220, "width": 55, "height": 20, "conf": 92},
    {"text": "heats",      "left": 162, "top": 220, "width": 48, "height": 20, "conf": 90},
    {"text": "up",         "left": 217, "top": 220, "width": 22, "height": 20, "conf": 95},
]

grading_result = {
    "score": 7,
    "max_score": 10,
    "feedback": (
        "Good attempt. Evaporation and precipitation were identified correctly. "
        "However, clouds form due to condensation, not gravity."
    ),
    "spelling_mistakes": ["evapration"],
    "wrong_parts": ["clouds form due to gravity"],
    "correct_parts": ["Water heats up"],
}

annotation_items = build_annotation_map(grading_result, word_map)

print("Annotation items built:")
for item in annotation_items:
    has_coords = item["coordinates"] is not None
    print(f"  {item['annotation_type']:14}  coords={'yes' if has_coords else 'no (region fallback)'}  {item['text']!r}")

questions = [
    {
        "annotation_items": annotation_items,
        "score": grading_result["score"],
        "max_score": grading_result["max_score"],
        "feedback": grading_result["feedback"],
        "region": {"left": 80, "top": 140, "width": 340, "height": 115},
        "page_index": 0,
    }
]

reliability_info = {"score": 73.0, "level": "medium"}

output = annotate_pdf(PDF_PATH, OUTPUT_PATH, questions, reliability_info=reliability_info, dpi=DPI)
assert os.path.exists(output)

print(f"\nAnnotated PDF saved to: {output}")
print("Open with: open samples/annotated_test.pdf")
print()
print("Page 1 should show:")
print("  - orange '?' left of the answer region (partial credit marker)")
print("  - red circle over 'evapration' (around y=150)")
print("  - red strikethrough line through 'clouds form due to gravity' (around y=185)")
print("  - green highlight over 'Water heats up' (around y=220)")
print("  - red score badge '7/10' to the right of the answer region")
print("  - yellow sticky note icon with feedback (click it in Preview)")
print("  - reliability stamp in top-right corner: '73% — MEDIUM'")
print()
print("Last page should show:")
print("  - Grading Summary with total score, grade letter, reliability, Q1 breakdown")

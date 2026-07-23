"""
Grades a handwritten exam paper with no pre-supplied rubric.
Gemini reads the printed questions, the handwritten answers, and grades them.

Usage:
    PYTHONPATH=. python grade_no_rubric.py samples/paper1.pdf
"""
import io
import json
import logging
import os
import sys

from google import genai
from google.genai import types

import config
from utils.pdf_utils import validate_pdf, convert_pdf_to_images

_VISION_MODEL = "gemini-2.5-flash"   # use the strongest model for vision grading
from workers.annotator_worker import annotate_pdf

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PDF_PATH   = sys.argv[1] if len(sys.argv) > 1 else "samples/paper1.pdf"
OUTPUT_PATH = PDF_PATH.replace(".pdf", "_marked.pdf")
DPI = 300

_SCHEMA = """\
Return ONLY valid JSON in this exact structure — no markdown, no explanation:
{
  "questions": [
    {
      "label": "1(a)",
      "page_index": 0,
      "region_top_fraction": 0.05,
      "region_bottom_fraction": 0.45,
      "score": 1,
      "max_score": 1,
      "feedback": "Correct. Method and answer both accurate.",
      "correct_parts": ["(5/6)^6 × 1/6"],
      "wrong_parts": [],
      "spelling_mistakes": []
    }
  ]
}

Field notes:
- label: question label exactly as printed (e.g. "1(a)", "2(b)(ii)")
- page_index: 0-based page number where the student's answer appears
- region_top_fraction: fraction of page height where the answer region starts (0.0 = top)
- region_bottom_fraction: fraction of page height where the answer region ends (1.0 = bottom)
- score: marks awarded (may use 0.5 increments)
- max_score: marks available as shown in brackets on the paper e.g. [2]
- feedback: concise, specific feedback referencing the student's working
- correct_parts: key correct steps or values the student wrote
- wrong_parts: key incorrect steps or values the student wrote
- spelling_mistakes: any misspelled mathematical terms"""

_PROMPT = f"""\
You are a Cambridge A-Level examiner marking a student's statistics paper.

The exam paper has PRINTED questions (with marks in square brackets) and \
HANDWRITTEN student answers. All pages of the paper are provided as images.

Your tasks:
1. Read every printed question carefully, noting the sub-question label and the \
   mark allocation in brackets.
2. Read the student's handwritten working and answer for each sub-question.
3. Mark each sub-question:
   - Check the method (working shown) AND the final answer
   - Award method marks for correct approach even if arithmetic slips occur
   - Deduct marks for wrong method, wrong answer, or missing required steps
   - Be fair but rigorous — this is a real exam
4. For each sub-question, identify the approximate vertical region on the page \
   where the student's answer is written (as fractions of the page height).

{_SCHEMA}"""


def _pil_to_bytes(image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _call_gemini_multi_image(images: list) -> dict:
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    parts = [_PROMPT]
    for i, img in enumerate(images):
        parts.append(f"\n--- Page {i + 1} ---")
        parts.append(types.Part.from_bytes(data=_pil_to_bytes(img), mime_type="image/png"))

    response = client.models.generate_content(
        model=_VISION_MODEL,
        contents=parts,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return json.loads(response.text)


_MARGIN_LEFT  = 110   # px — room for tick/cross in left gutter
_MARGIN_RIGHT = 260   # px — room for score badge in right gutter

def _build_annotator_questions(gemini_questions: list, page_sizes: list[tuple]) -> list[dict]:
    """Convert Gemini output to the format annotate_pdf expects."""
    annotator_qs = []
    for q in gemini_questions:
        page_idx = int(q.get("page_index", 0))
        page_w, page_h = page_sizes[page_idx] if page_idx < len(page_sizes) else (2480, 3508)

        top_frac    = float(q.get("region_top_fraction", 0.05))
        bottom_frac = float(q.get("region_bottom_fraction", 0.95))

        region = {
            "left":   _MARGIN_LEFT,
            "top":    top_frac * page_h,
            "width":  page_w - _MARGIN_LEFT - _MARGIN_RIGHT,
            "height": (bottom_frac - top_frac) * page_h,
        }

        # Color-code the answer region based on score
        score     = q.get("score", 0)
        max_score = q.get("max_score", 1)
        ratio     = score / max_score if max_score else 0
        if ratio == 1.0:
            ann_type = "highlight"          # green — full marks
        elif ratio == 0.0:
            ann_type = "strikethrough"      # red line — zero marks
        else:
            ann_type = "partial_highlight"  # yellow — partial

        annotation_items = [{"text": "", "annotation_type": ann_type, "coordinates": None}]

        annotator_qs.append({
            "page_index":       page_idx,
            "region":           region,
            "annotation_items": annotation_items,
            "score":            score,
            "max_score":        max_score,
            "label":            q["label"],
            "feedback":         q.get("feedback", ""),
        })
    return annotator_qs


def run():
    logger.info("Validating PDF...")
    doc = validate_pdf(PDF_PATH)
    doc.close()

    logger.info("Converting pages to images (DPI=%d)...", DPI)
    images = convert_pdf_to_images(PDF_PATH, dpi=DPI)
    page_sizes = [img.size for img in images]   # (width_px, height_px)
    logger.info("%d pages loaded", len(images))

    cache_path = PDF_PATH.replace(".pdf", "_gemini_cache.json")
    if os.path.exists(cache_path):
        logger.info("Loading cached Gemini result from %s", cache_path)
        with open(cache_path) as f:
            result = json.load(f)
    else:
        logger.info("Sending all pages to Gemini for reading and grading...")
        result = _call_gemini_multi_image(images)
        with open(cache_path, "w") as f:
            json.dump(result, f, indent=2)
        logger.info("Gemini result cached to %s", cache_path)

    questions = result.get("questions", [])
    logger.info("Gemini returned %d graded sub-questions", len(questions))

    # Print summary to terminal
    print()
    total_score = sum(q.get("score", 0) for q in questions)
    total_max   = sum(q.get("max_score", 0) for q in questions)
    print(f"  {'Label':<10} {'Score':>7}  Feedback")
    print("  " + "-" * 70)
    for q in questions:
        print(f"  {q['label']:<10} {q.get('score', 0):>3}/{q.get('max_score', 0):<3}  {q.get('feedback', '')[:60]}")
    print("  " + "-" * 70)
    print(f"  {'TOTAL':<10} {total_score:>3}/{total_max:<3}")
    print()

    logger.info("Building annotation data...")
    annotator_qs = _build_annotator_questions(questions, page_sizes)

    # Reliability info not applicable for printed+handwritten exam
    reliability_info = None

    logger.info("Annotating PDF...")
    annotate_pdf(PDF_PATH, OUTPUT_PATH, annotator_qs, reliability_info, dpi=DPI)

    logger.info("Done. Marked PDF saved to: %s", OUTPUT_PATH)
    print(f"Open with: open {OUTPUT_PATH}")


if __name__ == "__main__":
    run()

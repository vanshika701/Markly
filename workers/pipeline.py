import logging

import numpy as np
import pdfplumber

from config import FUZZY_MATCH_THRESHOLD, RELIABILITY_THRESHOLD
from utils.image_utils import preprocess_for_ocr
from utils.ocr_utils import calculate_reliability_score, extract_word_data, get_reliability_level
from utils.pdf_utils import convert_pdf_to_images, detect_pdf_type, extract_pdf_words, validate_pdf
from utils.text_utils import build_annotation_map, parse_questions
from workers.annotator_worker import annotate_pdf
from workers.grader_worker import grade_mcq, grade_written, grade_written_handwritten

logger = logging.getLogger(__name__)

_HANDWRITTEN_DPI = 300
_TYPED_DPI = 72  # pdfplumber native coordinate space (PDF points = 1/72 inch)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_annotator_region(region: dict) -> dict:
    """Convert {left, top, right, bottom} → {left, top, width, height} for annotator."""
    return {
        "left": region["left"],
        "top": region["top"],
        "width": region["right"] - region["left"],
        "height": region["bottom"] - region["top"],
    }


def _words_in_region(words: list[dict], region: dict) -> list[dict]:
    """Return words whose bounding boxes overlap the given region."""
    return [
        w for w in words
        if w["left"] < region["right"]
        and w["left"] + w["width"] > region["left"]
        and w["top"] < region["bottom"]
        and w["top"] + w["height"] > region["top"]
    ]


def _ocr_text_for_region(words: list[dict], region: dict) -> str:
    return " ".join(w["text"] for w in _words_in_region(words, region))


# ---------------------------------------------------------------------------
# Per-type processing
# ---------------------------------------------------------------------------

def _process_typed(pdf_path: str) -> tuple:
    """
    Extract words and parse questions from a typed PDF using pdfplumber.
    Returns (parsed_questions, word_maps_per_page, reliability_info=None, pil_images=None, dpi).
    """
    word_maps: list[list[dict]] = []
    parsed_qs: list[dict] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            words = extract_pdf_words(page)
            word_maps.append(words)
            parsed_qs.extend(parse_questions(words, page_number=page_num))

    return parsed_qs, word_maps, None, None, _TYPED_DPI


def _process_handwritten(pdf_path: str) -> tuple:
    """
    Convert pages to images, preprocess with OpenCV, run Tesseract for coordinates,
    calculate reliability, and parse questions.
    Returns (parsed_questions, word_maps_per_page, reliability_info, pil_images, dpi).
    """
    pil_images = convert_pdf_to_images(pdf_path, dpi=_HANDWRITTEN_DPI)
    word_maps: list[list[dict]] = []
    parsed_qs: list[dict] = []
    all_words: list[dict] = []

    for page_num, pil_image in enumerate(pil_images):
        np_image = np.array(pil_image)
        preprocessed = preprocess_for_ocr(np_image)
        words = extract_word_data(preprocessed)
        word_maps.append(words)
        all_words.extend(words)
        parsed_qs.extend(parse_questions(words, page_number=page_num))

    reliability_score = calculate_reliability_score(all_words)
    reliability_level = get_reliability_level(reliability_score, RELIABILITY_THRESHOLD)
    reliability_info = {"score": reliability_score, "level": reliability_level}

    return parsed_qs, word_maps, reliability_info, pil_images, _HANDWRITTEN_DPI


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_pipeline(pdf_path: str, answer_key: dict, output_pdf_path: str) -> dict:
    """
    Grade a student PDF against an answer key.

    answer_key shape:
        {
          "questions": [
            {"number": 1, "type": "mcq",     "answer": "B", "marks": 2},
            {"number": 2, "type": "written",  "answer": "...", "rubric": "...", "marks": 10},
          ]
        }

    Returns:
        {
          "annotated_pdf_path": str,
          "pdf_type": "typed" | "handwritten",
          "reliability": {"score": float, "level": str} | None,
          "total_score": int,
          "total_max":   int,
          "questions":   [{"number", "type", "score", "max_score", "feedback", "confidence"}]
        }
    """
    doc = validate_pdf(pdf_path)
    pdf_type = detect_pdf_type(doc)
    doc.close()

    logger.info("PDF type detected: %s", pdf_type)

    key_by_number = {q["number"]: q for q in answer_key["questions"]}

    if pdf_type == "typed":
        parsed_qs, word_maps, reliability_info, pil_images, dpi = _process_typed(pdf_path)
    else:
        parsed_qs, word_maps, reliability_info, pil_images, dpi = _process_handwritten(pdf_path)

    logger.info("Parsed %d question(s) from PDF.", len(parsed_qs))

    annotator_questions: list[dict] = []
    grading_summary: list[dict] = []

    for parsed_q in parsed_qs:
        q_num = parsed_q["number"]
        key_entry = key_by_number.get(q_num)

        if key_entry is None:
            logger.warning("Q%d found in PDF but not in answer key — skipping.", q_num)
            continue

        page_idx = parsed_q["page"]
        region = parsed_q["region"]  # {left, top, right, bottom}
        page_words = word_maps[page_idx] if page_idx is not None and page_idx < len(word_maps) else []
        answer_text = _ocr_text_for_region(page_words, region)

        logger.info("Grading Q%d (type=%s, page=%s)", q_num, key_entry["type"], page_idx)

        if key_entry["type"] == "mcq":
            result = grade_mcq(answer_text, key_entry)
        elif pdf_type == "handwritten" and pil_images and page_idx is not None:
            result = grade_written_handwritten(pil_images[page_idx], answer_text, key_entry)
        else:
            result = grade_written(answer_text, key_entry)

        annotation_items = build_annotation_map(result, page_words, FUZZY_MATCH_THRESHOLD)

        annotator_questions.append({
            "page_index": page_idx if page_idx is not None else 0,
            "region": _to_annotator_region(region),
            "annotation_items": annotation_items,
            "score": result["score"],
            "max_score": result["max_score"],
            "feedback": result.get("feedback", ""),
        })

        grading_summary.append({
            "number": q_num,
            "type": key_entry["type"],
            "score": result["score"],
            "max_score": result["max_score"],
            "feedback": result.get("feedback", ""),
            "confidence": result.get("confidence"),
        })

    annotate_pdf(pdf_path, output_pdf_path, annotator_questions, reliability_info, dpi)

    total_score = sum(q["score"] for q in grading_summary)
    total_max = sum(q["max_score"] for q in grading_summary)

    logger.info("Pipeline complete. Score: %d/%d", total_score, total_max)

    return {
        "annotated_pdf_path": output_pdf_path,
        "pdf_type": pdf_type,
        "reliability": reliability_info,
        "total_score": total_score,
        "total_max": total_max,
        "questions": grading_summary,
    }

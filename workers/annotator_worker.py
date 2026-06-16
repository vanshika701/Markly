import fitz  # PyMuPDF

_GREEN  = (0.0, 0.7, 0.0)
_RED    = (1.0, 0.0, 0.0)
_ORANGE = (1.0, 0.5, 0.0)
_YELLOW = (1.0, 0.9, 0.0)
_WHITE  = (1.0, 1.0, 1.0)
_BLACK  = (0.0, 0.0, 0.0)
_GRAY   = (0.5, 0.5, 0.5)

_RELIABILITY_COLORS = {"high": _GREEN, "medium": _ORANGE, "low": _RED}
_GRADE_THRESHOLDS = [(90, "A"), (75, "B"), (60, "C"), (45, "D")]


def _to_rect(coords: dict, dpi: int) -> fitz.Rect:
    scale = 72 / dpi
    return fitz.Rect(
        coords["left"] * scale,
        coords["top"] * scale,
        (coords["left"] + coords["width"]) * scale,
        (coords["top"] + coords["height"]) * scale,
    )


def _draw_annotation(page: fitz.Page, item: dict, fallback_rect: fitz.Rect, dpi: int) -> None:
    rect = _to_rect(item["coordinates"], dpi) if item["coordinates"] else fallback_rect
    ann_type = item["annotation_type"]

    if ann_type == "highlight":
        page.draw_rect(rect, color=None, fill=_GREEN, fill_opacity=0.35)
    elif ann_type == "strikethrough":
        mid_y = (rect.y0 + rect.y1) / 2
        page.draw_line(
            fitz.Point(rect.x0, mid_y), fitz.Point(rect.x1, mid_y),
            color=_RED, width=2,
        )
    elif ann_type == "circle":
        page.draw_oval(rect, color=_RED, width=2)


def _draw_score_badge(page: fitz.Page, region_rect: fitz.Rect, score: int, max_score: int) -> None:
    badge_text = f"{score}/{max_score}"
    x0 = region_rect.x1 + 6
    y0 = region_rect.y0
    badge = fitz.Rect(x0, y0, x0 + 48, y0 + 18)
    page.draw_rect(badge, color=_RED, fill=_RED)
    page.insert_text(fitz.Point(x0 + 4, y0 + 13), badge_text, fontsize=10, color=_WHITE)


def _draw_sticky_note(page: fitz.Page, region_rect: fitz.Rect, feedback: str) -> None:
    point = fitz.Point(region_rect.x0, region_rect.y1 + 6)
    annot = page.add_text_annot(point, feedback)
    annot.set_colors(stroke=_YELLOW)
    annot.update()


def _draw_tick_or_cross(page: fitz.Page, x: float, y: float, score: int, max_score: int) -> None:
    if score == max_score:
        # Green tick: short down-left stroke, then long up-right stroke
        page.draw_line(fitz.Point(x, y + 7),  fitz.Point(x + 5, y + 14), color=_GREEN, width=2.5)
        page.draw_line(fitz.Point(x + 5, y + 14), fitz.Point(x + 14, y), color=_GREEN, width=2.5)
    elif score == 0:
        # Red cross: two diagonal strokes
        page.draw_line(fitz.Point(x, y),      fitz.Point(x + 14, y + 14), color=_RED, width=2.5)
        page.draw_line(fitz.Point(x + 14, y), fitz.Point(x, y + 14),      color=_RED, width=2.5)
    else:
        # Orange question mark for partial credit
        page.insert_text(fitz.Point(x, y + 14), "?", fontsize=14, color=_ORANGE)


def _draw_reliability_stamp(page: fitz.Page, reliability_info: dict) -> None:
    score = reliability_info["score"]
    level = reliability_info["level"].upper()
    color = _RELIABILITY_COLORS.get(reliability_info["level"], _GRAY)
    descriptions = {
        "HIGH":   "Word-level annotations are accurate.",
        "MEDIUM": "Word-level annotations are mostly accurate.",
        "LOW":    "Handwriting was difficult to process — annotations may be approximate.",
    }
    page_width = page.rect.width
    box = fitz.Rect(page_width - 215, 10, page_width - 10, 54)
    page.draw_rect(box, color=color, fill=color, fill_opacity=0.10)
    page.draw_rect(box, color=color, width=1)
    page.insert_text(
        fitz.Point(page_width - 210, 26),
        f"Handwriting Reliability: {score:.0f}% — {level}",
        fontsize=8, color=color,
    )
    page.insert_text(
        fitz.Point(page_width - 210, 40),
        descriptions.get(level, ""),
        fontsize=7, color=color,
    )


def _letter_grade(pct: float) -> str:
    for threshold, letter in _GRADE_THRESHOLDS:
        if pct >= threshold:
            return letter
    return "F"


def _draw_summary_page(doc: fitz.Document, questions: list[dict], reliability_info: dict | None) -> None:
    page = doc.new_page()
    W = page.rect.width

    total_score = sum(q["score"] for q in questions)
    total_max   = sum(q["max_score"] for q in questions)
    pct   = (total_score / total_max * 100) if total_max else 0
    grade = _letter_grade(pct)
    grade_color = _GREEN if grade in ("A", "B") else _ORANGE if grade == "C" else _RED

    page.insert_text(fitz.Point(50, 60), "Grading Summary", fontsize=20, color=_BLACK)
    page.draw_line(fitz.Point(50, 68), fitz.Point(W - 50, 68), color=_GRAY, width=0.5)

    page.insert_text(fitz.Point(50, 100),
                     f"Total Score:  {total_score} / {total_max}  ({pct:.1f}%)",
                     fontsize=14, color=_BLACK)
    page.insert_text(fitz.Point(50, 122), f"Grade:  {grade}", fontsize=14, color=grade_color)

    y = 150
    if reliability_info:
        level = reliability_info["level"].upper()
        rel_color = _RELIABILITY_COLORS.get(reliability_info["level"], _GRAY)
        page.insert_text(
            fitz.Point(50, y),
            f"Handwriting Reliability:  {reliability_info['score']:.0f}% — {level}",
            fontsize=11, color=rel_color,
        )
        y += 26

    y += 10
    page.insert_text(fitz.Point(50, y), "Question Breakdown", fontsize=12, color=_BLACK)
    page.draw_line(fitz.Point(50, y + 4), fitz.Point(W - 50, y + 4), color=_GRAY, width=0.3)
    y += 22

    for i, q in enumerate(questions, start=1):
        q_pct = (q["score"] / q["max_score"] * 100) if q["max_score"] else 0
        row_color = _GREEN if q["score"] == q["max_score"] else _RED if q["score"] == 0 else _ORANGE
        row_text = (
            f"Q{i}:  {q['score']}/{q['max_score']} ({q_pct:.0f}%)  —  {q['feedback']}"
        )
        page.insert_textbox(
            fitz.Rect(50, y - 2, W - 50, y + 32),
            row_text,
            fontsize=9,
            color=row_color,
            align=fitz.TEXT_ALIGN_LEFT,
        )
        y += 38


def annotate_pdf(
    original_pdf_path: str,
    output_pdf_path: str,
    questions: list[dict],
    reliability_info: dict | None = None,
    dpi: int = 300,
) -> str:
    doc = fitz.open(original_pdf_path)

    if reliability_info:
        _draw_reliability_stamp(doc[0], reliability_info)

    for q in questions:
        page = doc[q["page_index"]]
        region_rect = _to_rect(q["region"], dpi)

        for item in q["annotation_items"]:
            _draw_annotation(page, item, region_rect, dpi)

        _draw_score_badge(page, region_rect, q["score"], q["max_score"])
        _draw_sticky_note(page, region_rect, q["feedback"])
        _draw_tick_or_cross(page, region_rect.x0 - 22, region_rect.y0, q["score"], q["max_score"])

    _draw_summary_page(doc, questions, reliability_info)

    doc.save(output_pdf_path)
    doc.close()
    return output_pdf_path

import re
import statistics

from rapidfuzz import fuzz, process

QUESTION_NUMBER_RE = re.compile(r"^[Qq]?(\d+)([.):]?$|[.):]\s)")
OPTION_LABEL_RE = re.compile(r"^([A-Da-d])([.):]?$|[.):]\s)")

# Matches a leading "answer"/"option"/etc. label, as long as it's followed by
# a separator (space, punctuation) or the end of the string - so it doesn't
# eat the start of an unrelated word.
MCQ_PREFIX_RE = re.compile(r"^(answer|option|ans|opt)(?=[\s.:)]|$)")

# Common OCR misreads between digits and the letters used for MCQ options.
OCR_DIGIT_TO_LETTER = {
    "0": "o",
    "1": "i",
    "2": "z",
    "5": "s",
    "6": "g",
    "8": "b",
}


def normalize_mcq_answer(text: str) -> str:
    text = text.strip().lower()
    text = MCQ_PREFIX_RE.sub("", text)
    text = re.sub(r"[\s.():]+", "", text)
    return OCR_DIGIT_TO_LETTER.get(text, text)


def group_words_into_lines(words: list[dict], tolerance_ratio: float = 0.5) -> list[list[dict]]:
    if not words:
        return []

    median_height = statistics.median(w["height"] for w in words)
    tolerance = tolerance_ratio * median_height

    sorted_words = sorted(words, key=lambda w: w["top"])

    lines = [[sorted_words[0]]]
    line_top_sum = sorted_words[0]["top"]

    for word in sorted_words[1:]:
        line_top_avg = line_top_sum / len(lines[-1])
        if abs(word["top"] - line_top_avg) <= tolerance:
            lines[-1].append(word)
            line_top_sum += word["top"]
        else:
            lines.append([word])
            line_top_sum = word["top"]

    return [sorted(line, key=lambda w: w["left"]) for line in lines]


def line_text(line: list[dict]) -> str:
    return " ".join(w["text"] for w in line)


def group_lines_into_questions(lines: list[list[dict]], start_number: int = 1) -> list[dict]:
    questions = []
    current = None
    next_expected = start_number

    for line in lines:
        text = line_text(line)
        match = QUESTION_NUMBER_RE.match(text)

        if match and int(match.group(1)) == next_expected:
            current = {"number": next_expected, "lines": [line]}
            questions.append(current)
            next_expected += 1
        elif current is not None:
            current["lines"].append(line)

    return questions


def split_question_into_stem_and_options(question: dict) -> dict:
    stem_lines = []
    options = {}
    current_label = None
    next_expected = "A"

    for line in question["lines"]:
        text = line_text(line)
        match = OPTION_LABEL_RE.match(text)

        if match and match.group(1).upper() == next_expected:
            current_label = next_expected
            options[current_label] = [line]
            next_expected = chr(ord(next_expected) + 1)
        elif current_label is not None:
            options[current_label].append(line)
        else:
            stem_lines.append(line)

    return {
        "number": question["number"],
        "stem_lines": stem_lines,
        "options": options,
    }


def bounding_box(lines: list[list[dict]]) -> dict:
    all_words = [w for line in lines for w in line]
    return {
        "left": min(w["left"] for w in all_words),
        "top": min(w["top"] for w in all_words),
        "right": max(w["left"] + w["width"] for w in all_words),
        "bottom": max(w["top"] + w["height"] for w in all_words),
    }


_ANNOTATION_TYPES = {
    "spelling_mistakes": "circle",
    "wrong_parts": "strikethrough",
    "correct_parts": "highlight",
}


def match_word_to_coordinates(
    word: str, word_map: list[dict], threshold: int = 85
) -> dict | None:
    choices = [w["text"] for w in word_map]
    match = process.extractOne(word, choices, scorer=fuzz.ratio, score_cutoff=threshold)
    if match is None:
        return None
    _, _, index = match
    w = word_map[index]
    return {"left": w["left"], "top": w["top"], "width": w["width"], "height": w["height"]}


def match_phrase_to_coordinates(
    phrase: str, word_map: list[dict], threshold: int = 85
) -> dict | None:
    matched = [
        match_word_to_coordinates(word, word_map, threshold)
        for word in phrase.split()
    ]
    matched = [c for c in matched if c is not None]
    if not matched:
        return None
    left = min(c["left"] for c in matched)
    top = min(c["top"] for c in matched)
    right = max(c["left"] + c["width"] for c in matched)
    bottom = max(c["top"] + c["height"] for c in matched)
    return {"left": left, "top": top, "width": right - left, "height": bottom - top}


def build_annotation_map(
    grading_result: dict, word_map: list[dict], threshold: int = 85
) -> list[dict]:
    items = []
    for field, annotation_type in _ANNOTATION_TYPES.items():
        for text in grading_result.get(field, []):
            is_phrase = " " in text.strip()
            coords = (
                match_phrase_to_coordinates(text, word_map, threshold)
                if is_phrase
                else match_word_to_coordinates(text, word_map, threshold)
            )
            items.append({"text": text, "annotation_type": annotation_type, "coordinates": coords})
    return items


def parse_questions(words: list[dict], page_number: int | None = None, start_number: int = 1) -> list[dict]:
    lines = group_words_into_lines(words)
    questions = group_lines_into_questions(lines, start_number=start_number)

    results = []
    for q in questions:
        structured = split_question_into_stem_and_options(q)
        structured["region"] = bounding_box(q["lines"])
        structured["page"] = page_number
        results.append(structured)
    return results

import re
import statistics

QUESTION_NUMBER_RE = re.compile(r"^[Qq]?(\d+)([.):]?$|[.):]\s)")
OPTION_LABEL_RE = re.compile(r"^([A-Da-d])([.):]?$|[.):]\s)")


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

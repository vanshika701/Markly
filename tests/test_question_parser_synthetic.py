from utils.text_utils import parse_questions


def make_words(text_lines: list[str], line_height: float = 20, char_width: float = 10) -> list[dict]:
    words = []
    for i, text_line in enumerate(text_lines):
        top = i * line_height
        left = 0.0
        for token in text_line.split():
            width = len(token) * char_width
            words.append({"text": token, "left": left, "top": top, "width": width, "height": line_height * 0.8})
            left += width + char_width
    return words


# Q1: MCQ ("Q1." style). Q2: written ("Q2." style). Q3: written, BLANK (no answer
# before the next question marker). Q4: written ("4." bare-number style).
text_lines = [
    "Q1. What is 2 + 2?",
    "A) 3",
    "B) 4",
    "C) 5",
    "D) 6",
    "Q2. Explain photosynthesis.",
    "Plants use sunlight to make food.",
    "3) What is the capital of France?",
    "4. Name two prime numbers.",
    "2 and 3 are prime numbers.",
]

words = make_words(text_lines)
questions = parse_questions(words, page_number=1)

print(f"{len(words)} words -> {len(questions)} questions\n")
for q in questions:
    print(f"--- Question {q['number']} (page {q['page']}) ---")
    print("region:", {k: round(v, 1) for k, v in q["region"].items()})
    print("stem:")
    for line in q["stem_lines"]:
        print("   ", " ".join(w["text"] for w in line))
    print("options:", {label: " ".join(w["text"] for line in lines for w in line) for label, lines in q["options"].items()})
    print()


# Continuation page: numbering starts at 5, not 1.
text_lines_page2 = [
    "5. What is the boiling point of water?",
    "a. 90",
    "b. 100",
    "c. 110",
    "d. 120",
    "6. What is the freezing point of water?",
    "a. -10",
    "b. 0",
    "c. 10",
    "d. 20",
]
words_page2 = make_words(text_lines_page2)

broken = parse_questions(words_page2, page_number=2)
print(f"page 2, default start_number=1 -> {len(broken)} questions (bug)")

fixed = parse_questions(words_page2, page_number=2, start_number=5)
print(f"page 2, start_number=5 -> {len(fixed)} questions")
for q in fixed:
    print(f"  Question {q['number']}: stem={[' '.join(w['text'] for w in l) for l in q['stem_lines']]}, options={list(q['options'])}")

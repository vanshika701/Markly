import pdfplumber

from utils.pdf_utils import extract_pdf_words
from utils.text_utils import parse_questions, line_text

with pdfplumber.open("samples/typed.pdf") as pdf:
    page = pdf.pages[2]  # page 3
    words = extract_pdf_words(page)

# left column only, for now (this page is two-column)
mid = page.width / 2
left_words = [w for w in words if w["left"] + w["width"] < mid]

questions = parse_questions(left_words)

print(f"{len(left_words)} words -> {len(questions)} questions\n")
for q in questions:
    print(f"--- Question {q['number']} ---")
    print("stem:")
    for line in q["stem_lines"]:
        print("   ", line_text(line))
    print("options:")
    for label, lines in q["options"].items():
        text = " / ".join(line_text(line) for line in lines)
        print(f"    {label}: {text}")
    print()

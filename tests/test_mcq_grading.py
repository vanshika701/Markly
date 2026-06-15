from workers.grader_worker import grade_mcq

answer_key_entry = {"type": "mcq", "answer": "B", "marks": 2}

cases = [
    ("B", "exact match"),
    ("b", "lowercase"),
    ("option b", "verbose phrasing"),
    ("Option B", "verbose + uppercase"),
    ("8", "OCR noise: 8 instead of B"),
    ("C", "wrong option"),
    ("", "blank answer"),
]

for student_answer, label in cases:
    result = grade_mcq(student_answer, answer_key_entry)
    print(f"{label:28} student={student_answer!r:10} -> {result}")

print()

# Fill-in-the-blank, written answer with a minor OCR/spelling slip
fill_in_blank_key = {"type": "mcq", "answer": "evaporation", "marks": 5}
for student_answer, label in [
    ("evaporation", "exact"),
    ("Evporation", "minor typo"),
    ("condensation", "wrong word"),
]:
    result = grade_mcq(student_answer, fill_in_blank_key)
    print(f"{label:28} student={student_answer!r:14} -> {result}")

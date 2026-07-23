from workers.grader_worker import grade_written

answer_key_entry = {
    "type": "written",
    "answer": "The water cycle involves evaporation, condensation, and precipitation.",
    "rubric": "Award 3 marks for evaporation, 3 for condensation, 4 for precipitation",
    "marks": 10,
}

cases = [
    (
        "good",
        "Water evaporates from oceans and lakes due to heat from the sun. "
        "As it rises, it cools and condenses into clouds. "
        "Eventually the water falls back to the ground as precipitation, such as rain or snow.",
    ),
    (
        "partial",
        "Water heats up and evapration happens, then clouds form due to gravity "
        "and water falls as rain.",
    ),
    (
        "wrong",
        "Plants need sunlight and water to grow into trees.",
    ),
    (
        "blank",
        "",
    ),
]

for label, student_answer in cases:
    result = grade_written(student_answer, answer_key_entry)
    print(f"--- {label} ---")
    print(result)
    assert result["max_score"] == answer_key_entry["marks"]
    assert 0 <= result["score"] <= result["max_score"]
    print()

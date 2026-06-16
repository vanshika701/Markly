from utils.text_utils import build_annotation_map, match_phrase_to_coordinates, match_word_to_coordinates

# Synthetic Tesseract word map — simulates one line of handwritten text
word_map = [
    {"text": "Water",      "left": 50,  "top": 100, "width": 55, "height": 18, "conf": 92},
    {"text": "heats",      "left": 115, "top": 100, "width": 50, "height": 18, "conf": 90},
    {"text": "up",         "left": 175, "top": 100, "width": 25, "height": 18, "conf": 95},
    {"text": "and",        "left": 210, "top": 100, "width": 32, "height": 18, "conf": 93},
    {"text": "evaprat1on", "left": 252, "top": 100, "width": 85, "height": 18, "conf": 71},
    {"text": "happens",    "left": 347, "top": 100, "width": 65, "height": 18, "conf": 88},
    {"text": "clouds",     "left": 50,  "top": 130, "width": 58, "height": 18, "conf": 85},
    {"text": "form",       "left": 118, "top": 130, "width": 42, "height": 18, "conf": 87},
    {"text": "due",        "left": 170, "top": 130, "width": 32, "height": 18, "conf": 89},
    {"text": "to",         "left": 212, "top": 130, "width": 18, "height": 18, "conf": 91},
    {"text": "gravity",    "left": 240, "top": 130, "width": 62, "height": 18, "conf": 83},
]

print("--- 1. exact single-word match ---")
result = match_word_to_coordinates("Water", word_map)
print(result)
assert result is not None
assert result["left"] == 50
print("OK\n")

print("--- 2. near-match: Gemini flagged 'evapration', Tesseract read 'evaprat1on' ---")
result = match_word_to_coordinates("evapration", word_map)
print(result)
assert result is not None   # fuzz.ratio("evapration","evaprat1on") ~= 90, above threshold
assert result["left"] == 252
print("OK\n")

print("--- 3. no match: word absent from page ---")
result = match_word_to_coordinates("precipitation", word_map)
print(result)
assert result is None
print("OK\n")

print("--- 4. phrase match: merged bounding box ---")
result = match_phrase_to_coordinates("clouds form due to gravity", word_map)
print(result)
assert result is not None
assert result["left"] == 50                        # leftmost word: "clouds"
assert result["top"] == 130
assert result["left"] + result["width"] == 302     # rightmost edge: 240 + 62
print("OK\n")

print("--- 5. messy handwriting: threshold forces None ---")
# Force a very high threshold to simulate no match found (messy OCR)
result = match_word_to_coordinates("evapration", word_map, threshold=99)
print(result)
assert result is None
print("OK\n")

print("--- 6. build_annotation_map end-to-end ---")
grading_result = {
    "spelling_mistakes": ["evapration"],
    "wrong_parts": ["clouds form due to gravity"],
    "correct_parts": ["Water heats up"],
}
annotation_map = build_annotation_map(grading_result, word_map)
for item in annotation_map:
    print(item)

assert len(annotation_map) == 3

circle      = next(a for a in annotation_map if a["annotation_type"] == "circle")
strikethrough = next(a for a in annotation_map if a["annotation_type"] == "strikethrough")
highlight   = next(a for a in annotation_map if a["annotation_type"] == "highlight")

assert circle["coordinates"] is not None        # "evapration" matched "evaprat1on"
assert strikethrough["coordinates"] is not None  # all phrase words found
assert highlight["coordinates"] is not None     # "Water heats up" all found
print("OK")

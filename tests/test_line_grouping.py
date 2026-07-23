import cv2

from utils.ocr_utils import extract_word_data
from utils.text_utils import group_words_into_lines

image = cv2.imread("output/converted_pages/page_1.png", cv2.IMREAD_GRAYSCALE)
words = extract_word_data(image)
lines = group_words_into_lines(words)

print(f"{len(words)} words -> {len(lines)} lines\n")
for line in lines:
    text = " ".join(w["text"] for w in line)
    print(text)

colors = [
    (0, 0, 255), (0, 165, 255), (0, 255, 255),
    (0, 255, 0), (255, 0, 0), (255, 0, 255),
]

annotated = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
for i, line in enumerate(lines):
    x0 = min(w["left"] for w in line)
    y0 = min(w["top"] for w in line)
    x1 = max(w["left"] + w["width"] for w in line)
    y1 = max(w["top"] + w["height"] for w in line)
    color = colors[i % len(colors)]
    cv2.rectangle(annotated, (int(x0), int(y0)), (int(x1), int(y1)), color, 2)

out_path = "output/ocr_word_boxes/page_1_lines.png"
cv2.imwrite(out_path, annotated)
print(f"\nsaved -> {out_path}")

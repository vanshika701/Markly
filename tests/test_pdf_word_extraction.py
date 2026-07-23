import os

import cv2
import numpy as np
import pdfplumber

from utils.pdf_utils import convert_pdf_to_images, extract_pdf_words

output_dir = "output/pdf_word_boxes"
os.makedirs(output_dir, exist_ok=True)

dpi = 300
scale = dpi / 72  # PDF points -> image pixels

with pdfplumber.open("samples/typed.pdf") as pdf:
    page = pdf.pages[2]  # page 3 (0-indexed)
    words = extract_pdf_words(page)

print(f"{len(words)} words")
for w in words[:10]:
    print(w)

page_image = convert_pdf_to_images("samples/typed.pdf", dpi=dpi)[2]
annotated = cv2.cvtColor(np.array(page_image.convert("RGB")), cv2.COLOR_RGB2BGR)

for w in words:
    x = int(w["left"] * scale)
    y = int(w["top"] * scale)
    width = int(w["width"] * scale)
    height = int(w["height"] * scale)
    cv2.rectangle(annotated, (x, y), (x + width, y + height), (0, 0, 255), 2)

out_path = os.path.join(output_dir, "typed_page3_boxes.png")
cv2.imwrite(out_path, annotated)
print(f"saved -> {out_path}")

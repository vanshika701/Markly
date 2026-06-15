import os

import cv2
import numpy as np

from utils.ocr_utils import extract_word_data
from utils.pdf_utils import convert_pdf_to_images

output_dir = "output/ocr_word_boxes"
os.makedirs(output_dir, exist_ok=True)

images = {
    "page_1": cv2.imread("output/converted_pages/page_1.png", cv2.IMREAD_GRAYSCALE),
    "messy_scan": cv2.imread("output/preprocessed/messy_scan/4_deskewed.png", cv2.IMREAD_GRAYSCALE),
    "messy_scan1": cv2.imread("output/preprocessed/messy_scan1/4_deskewed.png", cv2.IMREAD_GRAYSCALE),
    "typed_pdf_page_1": np.array(convert_pdf_to_images("samples/typed.pdf")[0].convert("L")),
}

for name, image in images.items():
    words = extract_word_data(image)
    print(f"{name}: {len(words)} words")

    annotated = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    for word in words:
        x, y, w, h = word["left"], word["top"], word["width"], word["height"]
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 0, 255), 2)

    out_path = os.path.join(output_dir, f"{name}_boxes.png")
    cv2.imwrite(out_path, annotated)
    print(f"  saved -> {out_path}")

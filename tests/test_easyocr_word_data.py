import os

import cv2
import easyocr
import numpy as np

from utils.pdf_utils import convert_pdf_to_images

output_dir = "output/ocr_word_boxes"
os.makedirs(output_dir, exist_ok=True)

images = {
    "page_1": cv2.imread("output/converted_pages/page_1.png", cv2.IMREAD_GRAYSCALE),
    "messy_scan": cv2.imread("output/preprocessed/messy_scan/4_deskewed.png", cv2.IMREAD_GRAYSCALE),
    "messy_scan1": cv2.imread("output/preprocessed/messy_scan1/4_deskewed.png", cv2.IMREAD_GRAYSCALE),
    "typed_pdf_page_1": np.array(convert_pdf_to_images("samples/typed.pdf")[0].convert("L")),
}

reader = easyocr.Reader(["en"], gpu=False)

for name, image in images.items():
    results = reader.readtext(image)
    print(f"{name}: {len(results)} words")
    for bbox, text, conf in results[:10]:
        print(f"  text={text!r:20} conf={conf:.2f}")

    annotated = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    for bbox, text, conf in results:
        points = np.array(bbox, dtype=np.int32)
        cv2.polylines(annotated, [points], isClosed=True, color=(255, 0, 0), thickness=2)

    out_path = os.path.join(output_dir, f"{name}_easyocr_boxes.png")
    cv2.imwrite(out_path, annotated)
    print(f"  saved -> {out_path}")

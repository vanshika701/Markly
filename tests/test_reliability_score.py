import cv2

from utils.ocr_utils import extract_word_data, calculate_reliability_score, get_reliability_level

images = {
    "page_1.png (handwritten.pdf scan)": "output/converted_pages/page_1.png",
    "messy_scan (deskewed)": "output/preprocessed/messy_scan/4_deskewed.png",
    "messy_scan1 (deskewed)": "output/preprocessed/messy_scan1/4_deskewed.png",
}

for label, path in images.items():
    image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    words = extract_word_data(image)
    score = calculate_reliability_score(words)
    level = get_reliability_level(score)
    print(f"{label}: {len(words)} words, reliability_score={score:.1f}, level={level}")

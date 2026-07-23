import numpy as np
import pytesseract


def extract_word_data(
    image: np.ndarray,
    max_width_fraction: float = 0.35,
    max_height_fraction: float = 0.20,
    min_confidence_if_oversized: int = 60,
) -> list[dict]:
    height, width = image.shape[:2]
    max_width = max_width_fraction * width
    max_height = max_height_fraction * height

    raw = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    words = []
    for i in range(len(raw["text"])):
        text = raw["text"][i].strip()
        if not text:
            continue

        box_width = raw["width"][i]
        box_height = raw["height"][i]
        conf = raw["conf"][i]

        oversized = box_width > max_width or box_height > max_height
        if oversized and conf < min_confidence_if_oversized:
            continue

        words.append({
            "text": text,
            "left": raw["left"][i],
            "top": raw["top"][i],
            "width": box_width,
            "height": box_height,
            "conf": conf,
        })
    return words


def calculate_reliability_score(words: list[dict]) -> float:
    confidences = [w["conf"] for w in words if w["conf"] > 0]
    if not confidences:
        return 0.0
    return sum(confidences) / len(confidences)


def get_reliability_level(score: float, threshold: int = 60) -> str:
    if score >= 80:
        return "high"
    elif score >= threshold:
        return "medium"
    else:
        return "low"

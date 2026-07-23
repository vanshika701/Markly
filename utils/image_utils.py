import cv2
import numpy as np


def to_grayscale(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def denoise(image: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoising(image, h=10)


def enhance_contrast(image: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(image)


def detect_skew_angle(image: np.ndarray) -> float:
    coords = np.column_stack(np.where(image < 128))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    return angle


def deskew(image: np.ndarray) -> np.ndarray:
    angle = detect_skew_angle(image)
    height, width = image.shape[:2]
    center = (width // 2, height // 2)
    matrix = cv2.getRotationMatrix2D(center, -angle, 1.0)
    return cv2.warpAffine(
        image, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )


def preprocess_for_ocr(image: np.ndarray) -> np.ndarray:
    gray = to_grayscale(image)
    denoised = denoise(gray)
    contrast = enhance_contrast(denoised)
    return deskew(contrast)

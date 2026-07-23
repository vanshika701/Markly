import os
import fitz
import pdfplumber
from pdf2image import convert_from_path
from PIL.Image import Image


class PDFValidationError(Exception):
    """Raised when an uploaded file fails PDF validation checks."""


def validate_pdf(file_path: str, max_size_mb: int = 20) -> fitz.Document:
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > max_size_mb:
        raise PDFValidationError(
            f"File too large: {size_mb:.1f}MB exceeds the {max_size_mb}MB limit."
        )

    with open(file_path, "rb") as f:
        header = f.read(5)
    if header != b"%PDF-":
        raise PDFValidationError("File is not a valid PDF.")

    try:
        doc = fitz.open(file_path)
    except fitz.FileDataError as e:
        raise PDFValidationError(f"PDF appears to be corrupted: {e}")

    if doc.is_encrypted:
        doc.close()
        raise PDFValidationError("PDF is password-protected.")

    return doc


def detect_pdf_type(doc: fitz.Document, min_chars: int = 20) -> str:
    total_chars = sum(len(page.get_text().strip()) for page in doc)
    return "typed" if total_chars >= min_chars else "handwritten"


def convert_pdf_to_images(file_path: str, dpi: int = 300) -> list[Image]:
    # Assumes file_path has already passed validate_pdf() — no corruption/encryption checks here.
    return convert_from_path(file_path, dpi=dpi)


def extract_pdf_words(
    page: pdfplumber.page.Page,
    max_width_fraction: float = 0.5,
    max_height_fraction: float = 0.5,
) -> list[dict]:
    max_width = max_width_fraction * page.width
    max_height = max_height_fraction * page.height

    words = []
    for w in page.extract_words(x_tolerance=1):
        if w["width"] > max_width or w["height"] > max_height:
            continue
        words.append({
            "text": w["text"],
            "left": w["x0"],
            "top": w["top"],
            "width": w["width"],
            "height": w["height"],
        })
    return words

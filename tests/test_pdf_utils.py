import os
import tempfile
import fitz

from utils.pdf_utils import validate_pdf, detect_pdf_type, PDFValidationError


def make_valid_pdf(path):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello, this is a typed PDF.")
    doc.save(path)
    doc.close()


def make_blank_pdf(path):
    doc = fitz.open()
    doc.new_page()
    doc.save(path)
    doc.close()


def make_encrypted_pdf(path):
    doc = fitz.open()
    doc.new_page()
    doc.save(path, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="user")
    doc.close()


def make_corrupted_pdf(path):
    with open(path, "wb") as f:
        f.write(b"%PDF-1.7\nthis is not a real pdf body")


def make_non_pdf(path):
    with open(path, "w") as f:
        f.write("just a text file")


def check(label, path, **kwargs):
    try:
        doc = validate_pdf(path, **kwargs)
        doc.close()
        print(f"{label}: PASSED validation")
    except PDFValidationError as e:
        print(f"{label}: REJECTED -> {e}")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        valid_path = os.path.join(tmp, "valid.pdf")
        encrypted_path = os.path.join(tmp, "encrypted.pdf")
        corrupted_path = os.path.join(tmp, "corrupted.pdf")
        non_pdf_path = os.path.join(tmp, "not_a_pdf.txt")

        make_valid_pdf(valid_path)
        make_encrypted_pdf(encrypted_path)
        make_corrupted_pdf(corrupted_path)
        make_non_pdf(non_pdf_path)

        check("Valid PDF", valid_path)
        check("Encrypted PDF", encrypted_path)
        check("Corrupted PDF", corrupted_path)
        check("Non-PDF file", non_pdf_path)
        check("Oversized (limit=0MB)", valid_path, max_size_mb=0)

        print()
        blank_path = os.path.join(tmp, "blank.pdf")
        make_blank_pdf(blank_path)

        for label, path in [("Page with text", valid_path), ("Blank page", blank_path)]:
            doc = validate_pdf(path)
            pdf_type = detect_pdf_type(doc)
            doc.close()
            print(f"{label}: detected as '{pdf_type}'")

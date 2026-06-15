from utils.pdf_utils import validate_pdf, detect_pdf_type

samples = {
    "typed": "samples/typed.pdf",
    "handwritten": "samples/handwritten.pdf",
}

for expected_type, path in samples.items():
    doc = validate_pdf(path)
    detected = detect_pdf_type(doc)
    pages = doc.page_count
    doc.close()
    result = "OK" if detected == expected_type else "MISMATCH"
    print(f"[{result}] {path}: expected={expected_type}, detected={detected}, pages={pages}")

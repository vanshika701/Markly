"""
End-to-end pipeline test.
Usage:
    PYTHONPATH=. python tests/test_pipeline.py samples/your_pdf.pdf
"""
import json
import logging
import sys

from workers.pipeline import run_pipeline

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

PDF_PATH = sys.argv[1] if len(sys.argv) > 1 else "samples/handwritten.pdf"
OUTPUT_PATH = "samples/pipeline_output.pdf"

# Edit this answer key to match whatever PDF you're testing with.
ANSWER_KEY = {
    "questions": [
        {
            "number": 1,
            "type": "written",
            "answer": "The water cycle involves evaporation, condensation, and precipitation.",
            "rubric": "Award 3 marks for evaporation, 3 for condensation, 4 for precipitation.",
            "marks": 10,
        },
    ]
}

print(f"\nRunning pipeline on: {PDF_PATH}")
print(f"Output will be saved to: {OUTPUT_PATH}\n")

result = run_pipeline(PDF_PATH, ANSWER_KEY, OUTPUT_PATH)

print("\n=== Pipeline Result ===")
print(json.dumps(result, indent=2, default=str))
print(f"\nAnnotated PDF: {result['annotated_pdf_path']}")
print("Open it with: open", OUTPUT_PATH)

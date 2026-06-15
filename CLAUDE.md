# CLAUDE.md — AI Grading Engine Project Context

## How to Work With Me

**Teaching mode is ON.**

- I will do everything myself — you guide me through and provide code when I am ready
- Never write code for me directly — always explain what we are about to build, why it works, and what concepts I need to understand first
- Before each step, tell me what I need to learn to complete it (e.g. "before we write this, you should understand X, Y, Z")
- After explaining, ask if I am ready to proceed or want to go deeper
- Write code only after I confirm I understand the concept
- When you do write code, walk through it line by line — never dump it without explanation
- Point out where this code reflects real-world and industry practice
- At the end of each step, tell me:
  1. What I just learned
  2. What is coming next
  3. What I should read or watch to go deeper (papers, docs, videos)
- I am a complete beginner — assume zero prior knowledge unless I demonstrate otherwise
- If anything needs to be changed or set up before we can proceed, tell me explicitly

**Code quality is non-negotiable.**
Even though I am learning, the code we produce must be expert-grade — properly structured, documented, and production-aware. No shortcuts. Teach me to do it right the first time.

---

## My Machine

- **Hardware:** Apple MacBook with M1 chip (ARM architecture)
- **OS:** macOS
- This matters for every installation instruction — always give me the Mac M1 compatible version
- Homebrew is the preferred package manager for system-level tools
- Python should be managed via `pyenv` or installed via Homebrew — never system Python
- Docker Desktop for Mac (Apple Silicon version) is available
- Tesseract must be installed via Homebrew: `brew install tesseract`
- Ollama has a native Mac M1 build at ollama.com — runs efficiently on Apple Silicon
- OpenCV and pymupdf both have M1-compatible wheels on PyPI — no special flags needed
- pdf2image requires poppler: `brew install poppler`

---

## Project Overview

This is an **AI-powered assignment grading engine** — a backend microservice that:

1. Accepts a student PDF (handwritten or typed) and a teacher-provided answer key
2. For typed PDFs: extracts text and word coordinates using pdfplumber
3. For handwritten PDFs: runs two parallel tracks — Gemini reads and grades the handwriting from the image, Tesseract extracts word bounding box coordinates for annotation placement
4. Grades each question — MCQ via fuzzy match, written via Gemini API
5. Calculates a handwriting reliability score from Tesseract's per-word confidence averages
6. Annotates the original PDF with teacher-style remarks at word level where possible, region level as fallback
7. Returns the annotated PDF and a structured score JSON including the reliability score via a REST API

This is not a standalone app. It is a **microservice** that plugs into an existing edtech platform via two REST endpoints.

---

## This Is Not a Trained ML Model

This is a critical distinction to keep in mind at all times:

- We are **not training any model**
- We are **not fine-tuning any model**
- We are using **pre-trained models via API** (Gemini, Groq) or locally via Ollama
- The "intelligence" comes entirely from existing LLMs
- Our job is to build the pipeline around them: ingestion, extraction, prompting, annotation, delivery
- The only "training data" we need is the teacher's answer key, provided per assignment

However, the project must be treated as **production-grade, high-accuracy software**. Accuracy comes from:
- Gemini Vision reading handwriting directly (much more accurate than Tesseract for messy writing)
- Good OCR preprocessing (OpenCV) to maximise Tesseract's coordinate accuracy
- Well-engineered prompts to the LLM
- Structured rubrics in the answer key
- Confidence thresholds and human review fallback
- Reliability scoring that is honest about annotation precision

---

## Integration-First Mindset

Every decision in this project must be made with integration in mind.

- The main edtech platform can be built in any language or framework — our engine must not assume anything about it
- We expose exactly two REST endpoints: `POST /grade` and `GET /result/{job_id}`
- We never handle auth — the platform handles that before calling us
- We never store user data — we store only PDFs and return URLs
- Response schemas must be stable and versioned — breaking changes break the platform
- Always design for the platform team to be able to integrate without reading our internal code
- The submission popup (guiding students to write neatly) is the main platform's responsibility — we just process what we receive and report reliability honestly

---

## The Dual Track — Most Important Architecture Decision

For handwritten PDFs, Gemini and Tesseract run in parallel and do completely different jobs. Never confuse their roles.

**Gemini — Track A (reading and grading):**
- Receives the page as an image
- Reads the actual handwriting content accurately
- Understands meaning, grades the answer, identifies spelling mistakes and wrong phrases
- Returns: score, feedback, confidence, spelling_mistakes list, correct_parts list, wrong_parts list
- Gemini is the source of truth for WHAT is wrong

**Tesseract — Track B (finding coordinates only):**
- Receives the cleaned image after OpenCV preprocessing
- Its text accuracy does not matter here — only its bounding box output matters
- Returns: word → (x, y, width, height) map + per-word confidence scores
- Tesseract is the source of truth for WHERE things are on the page

**Joining them:**
- For each word Gemini flags (e.g. "evapration" is a spelling mistake)
- Use rapidfuzz to find the closest matching word in Tesseract's bounding box map
- If similarity >= FUZZY_MATCH_THRESHOLD (default 85%) → use those coordinates for the circle
- If no match found → fall back to annotating the whole answer region

**Reliability score:**
- Average all Tesseract per-word confidence scores across the submission
- This tells us how trustworthy the coordinate matching is
- Above 80% → word-level annotation is reliable
- 60–80% → mostly reliable
- Below 60% → region-level fallback, flag for teacher review

---

## Technology Decisions — Fixed


| Layer | Decision | Reason |
|---|---|---|
| API Framework | FastAPI | Python-native, async, automatic docs |
| OCR (coordinates only) | Tesseract via pytesseract | Free, local, no rate limits — used for bounding boxes not text accuracy |
| Image preprocessing | OpenCV | Industry standard for scan cleanup |
| PDF to images | pdf2image | Required step before both Tesseract and Gemini vision |
| Typed PDF parsing | pdfplumber | Gives text + exact coordinates for typed PDFs |
| MCQ grading | rapidfuzz | Fast, accurate fuzzy matching, free |
| Word coordinate matching | rapidfuzz | Matches Gemini-flagged words to Tesseract bounding boxes |
| Handwriting reading + grading | Gemini 1.5 Flash | Vision capability reads handwriting accurately, free tier |
| LLM fallback | Groq (Llama 3.1) | Fast, generous free tier |
| Local LLM | Ollama | Runs natively on M1, free, no rate limits |
| PDF annotation | pymupdf (fitz) | Most capable free PDF manipulation library |
| Job queue | Celery + Redis | Industry standard async task processing |
| File storage | Cloudflare R2 | S3-compatible, free egress, affordable |
| Config management | python-dotenv | Simple, standard |

---

## LLM Provider Hierarchy

```
1. Gemini 1.5 Flash  →  primary (1500 req/day free, has vision for handwriting)
2. Groq / Llama 3.1  →  fallback if Gemini rate-limited (uses Tesseract text, no vision)
3. Ollama (local)    →  fallback if no internet / both APIs down (uses Tesseract text, no vision)
```

Switching providers = one environment variable (`LLM_PROVIDER`). The rest of the codebase never changes.

When Groq or Ollama are used as fallback for handwritten PDFs, Tesseract text is used for grading instead of Gemini vision. This is less accurate for messy handwriting — the reliability score will reflect this.

---

## API Keys — All Free

| Service | Where to get it | Cost |
|---|---|---|
| Gemini API | aistudio.google.com | Free, no credit card |
| Groq API | console.groq.com | Free, no credit card |
| Ollama | ollama.com (download app) | Free, runs locally |
| Cloudflare R2 | cloudflare.com | Free up to 10GB |

All keys go in `.env` — never hardcoded, never committed to git.

---

## Project File Structure

```
grading-engine/
├── main.py                      # FastAPI app and endpoint definitions
├── config.py                    # All environment variable loading
├── requirements.txt             # Python dependencies
├── .env                         # Secret keys — NEVER commit this
├── .env.example                 # Safe template to commit
├── docker-compose.yml           # Spins up API + worker + Redis
├── Dockerfile
│
├── workers/
│   ├── pipeline.py              # Main Celery task — orchestrates all steps
│   ├── ocr_worker.py            # OpenCV preprocessing + Tesseract (coordinates + reliability score)
│   ├── parser_worker.py         # Question detection, answer-to-question mapping
│   ├── grader_worker.py         # MCQ fuzzy match + LLM written grading
│   ├── reliability_worker.py    # Calculates and attaches reliability score
│   └── annotator_worker.py      # pymupdf: word-level and region-level annotation
│
├── services/
│   ├── llm_service.py           # Abstracted LLM caller — swaps providers transparently
│   ├── storage_service.py       # Cloudflare R2 upload/download
│   └── cache_service.py         # Caches graded answers to reduce API calls
│
└── utils/
    ├── pdf_utils.py             # PDF validation, page coordinate helpers
    ├── image_utils.py           # OpenCV helper functions
    └── text_utils.py            # Fuzzy matching, word coordinate matching, question parsers
```

---

## The Two API Endpoints — Memorise These

### POST /grade
Accepts: student PDF file + answer key JSON
Returns: job_id and status "processing"

### GET /result/{job_id}
Returns: status + reliability_score + reliability_level + graded PDF URL + score breakdown JSON

The main platform calls POST /grade on student submission, then polls GET /result/{job_id} every few seconds until status is "graded", "review_needed", or "failed".

---

## Pipeline Steps — In Order

1. Validate PDF (real PDF? not corrupted? not password protected? under size limit?)
2. Convert PDF pages to images (pdf2image)
3. Determine type: typed or handwritten
4. If typed:
   - pdfplumber extracts text + exact word coordinates
   - annotation_level = "exact"
5. If handwritten, run two parallel tracks:
   - Track A: send page images to Gemini → reads handwriting → returns grades + flagged words/phrases
   - Track B: OpenCV cleans image → Tesseract OCR → returns word bounding boxes + per-word confidence
   - Calculate reliability score from Track B confidence averages
   - Join tracks: rapidfuzz matches each Gemini-flagged word to Tesseract bounding box
   - annotation_level = "word" if reliability >= 60%, "region" if below
6. Parse question boundaries from extracted text or Gemini response
7. Map each answer to its question number and coordinates
8. For each question:
   - MCQ → rapidfuzz match against answer key → score
   - Written → Gemini grades + returns structured JSON with flagged words
9. Check grading confidence: below CONFIDENCE_THRESHOLD → flag for review
10. Check reliability score: below RELIABILITY_THRESHOLD → flag for review
11. pymupdf annotates original PDF:
    - word-level circles, highlights, strikethroughs where coordinates matched
    - region-level fallback where coordinates could not be matched
    - reliability stamp on page 1
    - score badge and sticky note per question
    - summary page at end
12. Save graded PDF to Cloudflare R2
13. Update job status to "graded" or "review_needed"

---

## What the LLM Returns Per Question

```json
{
  "score": 7,
  "max_score": 10,
  "feedback": "Good explanation of evaporation. Missed condensation.",
  "confidence": 0.88,
  "spelling_mistakes": ["evapration", "percipitation"],
  "correct_parts": ["Water heats up and rises into the atmosphere"],
  "wrong_parts": ["clouds form due to gravity"]
}
```

This structured response drives all annotation decisions. The LLM is always prompted to return exactly this JSON and nothing else. If the response is malformed, retry once then fall back to next provider.

---

## Annotation Types We Support

| Annotation | Tool | Precision | Triggered By |
|---|---|---|---|
| Green highlight | pymupdf highlight | Word or region | LLM marks section as correct |
| Red strikethrough | pymupdf strikethrough | Word or region | LLM marks section as wrong |
| Red circle | pymupdf draw oval | Word or region | LLM flags spelling mistake |
| Yellow highlight | pymupdf highlight | Word or region | LLM marks partial credit |
| Blue underline | pymupdf underline | Word or region | LLM marks incomplete-but-good |
| ✓ green tick | pymupdf insert_text | Per question | Full score on question |
| ✗ red cross | pymupdf insert_text | Per question | Zero score on question |
| ? orange | pymupdf insert_text | Per question | Low confidence or low reliability |
| Score badge | pymupdf draw_rect + text | Per question | Always |
| Sticky note | pymupdf text_annot | Per question | Always |
| Reliability stamp | pymupdf insert_text | Page 1 | Always for handwritten |
| Summary page | pymupdf new_page | End of doc | Always |

---

## Reliability Score Logic

```
Tesseract per-word confidence scores → average → reliability_score (0–100)

reliability_score >= 80  → level: "high"    → word-level annotation, no flag
reliability_score 60–79  → level: "medium"  → word-level annotation, no flag
reliability_score < 60   → level: "low"     → region-level annotation, flag for review
```

Configurable via environment variable `RELIABILITY_THRESHOLD=60`.

---

## Confidence vs Reliability — Know the Difference

These are two separate scores that serve different purposes:

**Grading Confidence** (from LLM):
- How sure is the AI that the grade it gave is correct?
- Per question
- Below CONFIDENCE_THRESHOLD → flag that question for teacher review

**Handwriting Reliability** (from Tesseract):
- How accurately can we place word-level annotations on the page?
- Per submission (overall)
- Below RELIABILITY_THRESHOLD → use region-level fallback, flag whole submission

Both are independent. A submission can have high grading confidence (Gemini understood the answer well) but low reliability (handwriting was too messy for Tesseract to find word coordinates).

---

## Edge Cases to Always Handle

- PDF is corrupted → reject early, return clear error
- PDF is password protected → reject early, return clear error
- Tesseract finds no words at all → skip word matching, use full-region annotation, flag for review
- No fuzzy match found above threshold → fall back to region annotation for that word
- Student leaves a question blank → assign zero with note "no answer provided"
- LLM returns malformed JSON → retry once, then fall back to next provider
- Gemini rate limit hit → switch to Groq automatically, use Tesseract text for grading, log event
- Groq rate limit hit → switch to Ollama automatically, log event
- PDF has no detectable question boundaries → flag entire submission for manual grading
- Reliability below 60% → region-level annotation, flag for teacher review
- File too large (over 20MB) → reject early with clear message
- Non-PDF file uploaded → reject early with clear message

---

## Things We Never Do

- Never modify the original uploaded PDF — only create new annotated copies
- Never store student answer content in a database — only file URLs and scores
- Never hardcode API keys anywhere in code
- Never do grading synchronously inside an HTTP request — always use Celery
- Never assume the PDF is typed — always detect first
- Never use Tesseract text for grading on handwritten PDFs when Gemini is available
- Never pretend word-level annotation is accurate when reliability is low — always report honestly
- Never expose internal error messages to the API response — log them, return clean errors

---

## Development Order (Build This Way)

Phase 1 — Core pipeline, no async yet:
1. PDF validation and type detection
2. pdf2image conversion
3. OpenCV preprocessing
4. Tesseract OCR — extract word bounding boxes + confidence scores
5. pdfplumber extraction for typed PDFs
6. Reliability score calculation
7. Question parser
8. MCQ grading with rapidfuzz
9. LLM service abstraction layer
10. Written grading with Gemini (text first, then add vision for handwriting)
11. Word coordinate matching with rapidfuzz
12. pymupdf annotation — word level and region level
13. FastAPI endpoints (synchronous first)

Phase 2 — Production hardening:
14. Celery + Redis async job queue
15. Groq fallback
16. Ollama fallback
17. Confidence threshold and reliability threshold flagging
18. Answer caching
19. Cloudflare R2 storage
20. Full error handling and edge cases
21. Docker + Docker Compose

---

## Resources to Keep Handy

- pymupdf docs: https://pymupdf.readthedocs.io
- Tesseract docs: https://tesseract-ocr.github.io
- Gemini API docs (including vision): https://ai.google.dev/docs
- Groq API docs: https://console.groq.com/docs
- Ollama docs: https://ollama.com/library
- FastAPI docs: https://fastapi.tiangolo.com
- Celery docs: https://docs.celeryq.dev
- pdfplumber docs: https://github.com/jsvine/pdfplumber
- rapidfuzz docs: https://rapidfuzz.github.io/RapidFuzz
- Cloudflare R2 docs: https://developers.cloudflare.com/r2
- OpenCV Python docs: https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html

---

## Mac M1 Installation Notes

When installing system dependencies always use Homebrew:

```bash
brew install tesseract
brew install poppler          # required by pdf2image
brew install redis            # for Celery broker
```

Python packages via pip work normally on M1. OpenCV and pymupdf both have M1-compatible wheels on PyPI — no special flags needed.

Docker Desktop must be the Apple Silicon version downloaded from docker.com/products/docker-desktop.

Ollama runs natively on M1 with GPU acceleration — download from ollama.com, not via pip.

pyenv is recommended for Python version management:
```bash
brew install pyenv
pyenv install 3.11.9
pyenv global 3.11.9
```

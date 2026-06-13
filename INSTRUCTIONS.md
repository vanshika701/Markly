# AI Assignment Grading Engine — Project Instructions

## What This Project Is

A self-contained AI-powered assignment grading engine that plugs into an existing edtech platform. It accepts student assignment PDFs (both handwritten and typed), grades them against a teacher-provided answer key using AI, annotates the original PDF with remarks exactly like a human teacher would — including word-by-word spelling circles, correct/wrong highlights, ticks, crosses, and score badges — and returns the graded PDF along with a structured score breakdown.

This is not a standalone app. It is a **grading microservice** — the edtech platform sends it a PDF, it sends back a graded PDF and scores. Everything in between is handled internally.

---

## What It Does — Full Feature List

### Core Pipeline
- Accepts student PDF uploads (handwritten or computer-generated)
- Detects whether the PDF is typed or handwritten and routes accordingly
- Extracts text and exact word coordinates from typed PDFs using pdfplumber
- For handwritten PDFs, runs two parallel tracks:
  - Track A: sends page images directly to Gemini for accurate reading and grading
  - Track B: runs Tesseract OCR to extract word-level bounding box coordinates for annotation placement
- Preprocesses handwritten scans using OpenCV before OCR (grayscale, denoise, deskew, contrast enhancement)
- Detects and parses question boundaries automatically (Q1, Q2, 1., 2., etc.)
- Maps each student answer to its question number and page coordinates
- Grades MCQ and fill-in-the-blank answers using fuzzy string matching (no AI needed)
- Grades written and descriptive answers using the Gemini 1.5 Flash API
- Falls back to Groq API (Llama 3.1 70B) if Gemini hits rate limits
- Falls back to local Ollama if both APIs are unavailable
- Returns a grading confidence score per question — low confidence answers are flagged for teacher review
- Calculates a handwriting reliability score per submission based on Tesseract word-level confidence averages
- Caches similar answers to avoid redundant API calls

### Student Submission Popup (Frontend Responsibility)
The main platform must show this popup before every handwritten PDF upload:

```
📝 Before you upload your assignment

To ensure accurate grading and precise word-by-word feedback:

  ✓  Write in clear block / print letters
  ✓  Do not use cursive or joined handwriting
  ✓  Leave a clear space between each word
  ✓  Use a ruled copy — write on the lines
  ✓  Use a dark pen (black or blue)
  ✓  Scan in good lighting or use a flatbed scanner

This helps our system give you word-by-word feedback
exactly like a teacher would mark your paper.

[ I understand, proceed to upload ]
```

This is a UX decision that significantly improves word-level annotation accuracy.

### Handwriting Reliability Score
Every handwritten submission receives a reliability score calculated from Tesseract's per-word confidence output:

| Score | Level | Meaning |
|---|---|---|
| 80% and above | High | Word-level remarks are accurate |
| 60% to 79% | Medium | Word-level remarks are mostly accurate |
| Below 60% | Low | Handwriting was difficult to process — word-level remarks may be approximate |

This score is:
- Stamped visibly on page 1 of the graded PDF
- Included in the API response JSON
- Used to automatically flag low-reliability submissions for teacher review

### Three-Tier Annotation Precision
Annotation precision adapts based on handwriting quality — it never breaks, it gracefully degrades:

| Situation | Annotation Level | Method |
|---|---|---|
| Typed PDF | Word level — perfect | pdfplumber exact coordinates |
| Neat handwriting | Word level — high accuracy | Tesseract boxes + rapidfuzz match to Gemini-flagged words |
| Messy handwriting | Region/phrase level | Gemini identifies answer regions, pymupdf annotates regions |

### PDF Annotation (Teacher-Style Remarks)
- Green highlight over correct answer sections
- Red strikethrough over wrong concepts or incorrect statements
- Red circles around individual spelling mistakes (word level where possible, region level fallback)
- Yellow highlight over partially correct sections
- Blue underline over good but incomplete points
- Score badge (e.g. 8/10) placed next to each answer
- Sticky note with detailed AI-generated feedback per question
- Tick (✓) in green for fully correct answers
- Cross (✗) in red for wrong answers
- Question mark (?) in orange for flagged/uncertain answers
- Handwriting reliability score stamped on page 1
- Summary page appended at the end with total score, grade, reliability level, and per-question breakdown
- Original PDF is never modified — annotated version is always a separate file

### Assignment Type Support
- MCQ (multiple choice)
- Short written answers
- Long descriptive/essay answers
- Mixed assignments (MCQ and written questions in the same PDF)

### Trigger Modes
- Auto-grade — fires immediately when student submits
- Manual grade — teacher clicks grade button on their platform dashboard
- Both modes supported via the same API

### Teacher Review Flow
- Low grading confidence → flagged with status `review_needed`
- Low handwriting reliability (below 60%) → also flagged for teacher review
- Flagged submissions appear in the teacher review queue on the main platform
- Teacher can override any AI-assigned score
- Teacher can add their own remarks on top of AI remarks

---

## System Architecture

```
Student PDF  +  Answer Key
         ↓
    [ FastAPI ]
    POST /grade
         ↓
    [ Celery Worker ]
         ↓
    ┌─────────────────────────────────────────────┐
    │                  PIPELINE                   │
    │                                             │
    │  1. Validate PDF                            │
    │  2. Convert pages to images (pdf2image)     │
    │  3. Detect: typed or handwritten?           │
    │                                             │
    │  TYPED PATH:                                │
    │    pdfplumber → text + exact coordinates    │
    │                                             │
    │  HANDWRITTEN PATH (two parallel tracks):    │
    │    Track A: page image → Gemini             │
    │             reads handwriting accurately    │
    │             returns grades + flagged words  │
    │    Track B: OpenCV clean → Tesseract OCR    │
    │             returns word bounding boxes     │
    │             + per-word confidence scores    │
    │    Join: match Gemini-flagged words to      │
    │          Tesseract coordinates via          │
    │          rapidfuzz fuzzy matching           │
    │                                             │
    │  4. Parse questions Q1/Q2/Q3               │
    │  5. For each question:                      │
    │     MCQ → rapidfuzz match                  │
    │     Written → Gemini grades + flags words  │
    │  6. Calculate reliability score             │
    │  7. Confidence + reliability checks         │
    │     → flag for review if either is low     │
    │  8. pymupdf annotates original PDF          │
    │     word-level where possible               │
    │     region-level as fallback               │
    │  9. Save graded PDF to storage              │
    └─────────────────────────────────────────────┘
         ↓
    [ GET /result/{job_id} ]
    Returns score JSON + reliability score + graded PDF URL
```

---

## How Handwriting is Handled — The Dual Track

For handwritten PDFs, Gemini and Tesseract each do a separate job simultaneously:

**Gemini's job (Track A) — reading and grading:**
Gemini receives the page as an image. It reads the handwriting accurately (far better than Tesseract), understands the meaning, grades the answer, and returns a list of flagged words and phrases — spelling mistakes, wrong concepts, correct sections.

**Tesseract's job (Track B) — finding coordinates:**
Tesseract does not need to read the handwriting accurately. Its only job is to detect where words are on the page and return bounding box coordinates. Even if it misreads "evaporation" as "evaprat1on", it still gives us an approximate box at the right location.

**How they join:**
When Gemini says the word "evapration" is a spelling mistake, your code uses rapidfuzz to find the closest matching word in Tesseract's bounding box output. If similarity is above 85%, it uses those coordinates to draw the red circle. If no close match is found, it falls back to annotating the whole answer region instead of the specific word.

This approach gives word-level precision when handwriting is clear, and region-level precision when it is messy — always producing useful, teacher-style markup regardless of input quality.

---

## LLM Provider Strategy

```
Primary   →  Gemini 1.5 Flash  (Google AI Studio — free tier, 1500 req/day)
Fallback  →  Groq / Llama 3.1  (Groq Console — free tier, ~14400 req/day)
Local     →  Ollama             (runs on your own machine, zero cost, no limits)
```

Switching between providers is a single environment variable change. The grading logic is identical regardless of provider.

**For handwritten PDFs**, Gemini is called with the page image (vision capability). Groq and Ollama receive the Tesseract-extracted text as fallback since they have weaker vision capabilities.

The LLM is called **once per written question**. It receives:
- The question text
- The answer key
- The rubric (marks per concept)
- The student's answer (as image for Gemini, as extracted text for Groq/Ollama)

It returns:
- Score (integer)
- Feedback (string)
- Confidence (float 0.0 to 1.0)
- Spelling mistakes identified (list of exact wrong words as Gemini read them)
- Wrong parts of the answer (phrases)
- Correct parts of the answer (phrases)

---

## Complete Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| API Framework | FastAPI | REST endpoints |
| API Server | Uvicorn | Runs FastAPI |
| Request Validation | Pydantic | Input/output schema |
| PDF to Images | pdf2image | Convert pages before OCR and Gemini vision |
| Image Preprocessing | OpenCV (cv2) | Clean handwritten scans before Tesseract |
| OCR (coordinates only) | Tesseract + pytesseract | Extract word bounding boxes from handwritten PDFs |
| Typed PDF Parsing | pdfplumber | Extract text + exact coordinates from typed PDFs |
| MCQ Grading | rapidfuzz | Fuzzy string matching |
| Word Coordinate Matching | rapidfuzz | Match Gemini-flagged words to Tesseract bounding boxes |
| Written Grading + Handwriting Reading | google-generativeai | Gemini 1.5 Flash API (vision + language) |
| LLM Fallback 1 | groq | Groq API / Llama 3.1 |
| LLM Fallback 2 | ollama | Local model, no internet needed |
| PDF Annotation | pymupdf (fitz) | Draw all remarks on PDF |
| Job Queue Broker | Redis | Holds async grading jobs |
| Background Workers | Celery | Processes grading pipeline asynchronously |
| File Storage | Cloudflare R2 via boto3 | Stores original and graded PDFs |
| Environment Config | python-dotenv | Manages API keys and settings |

---

## API Endpoints

These are the only two endpoints the main edtech platform needs to integrate with.

---

### POST /grade

Submit a student assignment for grading.

**Request (multipart/form-data):**

```
student_pdf     : file        (required) PDF file upload
answer_key      : JSON string (required) structured answer key
```

**Answer Key Format:**

```json
{
  "Q1": {
    "type": "mcq",
    "answer": "B",
    "marks": 2
  },
  "Q2": {
    "type": "written",
    "answer": "The water cycle involves evaporation, condensation, and precipitation.",
    "rubric": "Award 3 marks for evaporation, 3 for condensation, 4 for precipitation",
    "marks": 10
  },
  "Q3": {
    "type": "written",
    "answer": "Photosynthesis is the process by which plants convert sunlight into food.",
    "rubric": "Award 5 marks for mentioning sunlight, 5 for mentioning chlorophyll",
    "marks": 10
  }
}
```

**Response:**

```json
{
  "job_id": "abc123-def456",
  "status": "processing",
  "submitted_at": "2024-01-15T10:30:00Z"
}
```

---

### GET /result/{job_id}

Poll this endpoint to check grading status and retrieve results.

**Response when processing:**

```json
{
  "job_id": "abc123-def456",
  "status": "processing"
}
```

**Response when graded:**

```json
{
  "job_id": "abc123-def456",
  "status": "graded",
  "total_score": 17,
  "max_score": 22,
  "percentage": 77.3,
  "grade": "B",
  "reliability_score": 87,
  "reliability_level": "high",
  "reliability_message": "Word-level remarks on this submission are accurate",
  "graded_pdf_url": "https://your-storage/graded/abc123-def456.pdf",
  "graded_at": "2024-01-15T10:30:45Z",
  "breakdown": [
    {
      "question": "Q1",
      "type": "mcq",
      "score": 2,
      "max_score": 2,
      "feedback": "Correct"
    },
    {
      "question": "Q2",
      "type": "written",
      "score": 8,
      "max_score": 10,
      "feedback": "Good explanation of evaporation and condensation. Did not mention precipitation.",
      "spelling_mistakes": ["evapration"],
      "annotation_level": "word",
      "confidence": 0.92
    },
    {
      "question": "Q3",
      "type": "written",
      "score": 7,
      "max_score": 10,
      "feedback": "Mentioned sunlight correctly but missed chlorophyll entirely.",
      "spelling_mistakes": ["photosinthesis"],
      "annotation_level": "word",
      "confidence": 0.88
    }
  ]
}
```

**Response when flagged for teacher review:**

```json
{
  "job_id": "abc123-def456",
  "status": "review_needed",
  "reason": "Low handwriting reliability (54%). Word-level remarks may be inaccurate. Teacher review required."
}
```

**Response when failed:**

```json
{
  "job_id": "abc123-def456",
  "status": "failed",
  "error": "PDF appears to be corrupted or password protected."
}
```

---

## Possible Status Values

| Status | Meaning |
|---|---|
| `processing` | Job is in the queue or actively being graded |
| `graded` | Grading complete, results available |
| `review_needed` | Low grading confidence or low handwriting reliability — teacher review required |
| `failed` | Something went wrong, check error field |

---

## Annotation Level Values (Per Question in Breakdown)

| Value | Meaning |
|---|---|
| `word` | Circles and highlights placed at individual word level |
| `region` | Circles and highlights placed at answer region level (messy handwriting fallback) |
| `exact` | Typed PDF — perfectly precise word coordinates from pdfplumber |

---

## Integration Notes for the Main Platform

- Poll `GET /result/{job_id}` every 3–5 seconds until status is `graded`, `review_needed`, or `failed`
- The `graded_pdf_url` is a direct download link to the annotated PDF
- Display `reliability_level` and `reliability_message` to the student alongside the graded PDF
- Store the `job_id` in your database against the submission record
- The grading engine does not handle auth — the main platform verifies the request before calling these endpoints
- Show the submission popup before every handwritten PDF upload (see popup text in features section above)
- File size limit: 20MB per PDF
- Supported format: PDF only (.pdf)
- The engine accepts answers in any language — Hindi, regional languages, or mixed

---

## Colour Convention in Annotated PDFs

| Colour / Symbol | Meaning |
|---|---|
| Green highlight | Correct section |
| Red strikethrough | Wrong concept or incorrect statement |
| Red circle | Spelling mistake (word-level or region-level) |
| Yellow highlight | Partially correct |
| Blue underline | Good point but incomplete |
| ✓ Green tick | Full marks awarded for this question |
| ✗ Red cross | No marks for this question |
| ? Orange | Flagged — low confidence or low reliability |
| Reliability stamp | Page 1 — handwriting clarity score and level |

---

## Project Folder Structure

```
grading-engine/
├── main.py                      # FastAPI app, endpoint definitions
├── config.py                    # Environment variables, LLM provider selection
├── requirements.txt             # All Python dependencies
├── .env                         # API keys (never committed to git)
├── .env.example                 # Template for .env
├── docker-compose.yml           # Runs API + worker + Redis together
├── Dockerfile                   # Container definition
│
├── workers/
│   ├── pipeline.py              # Main Celery task, orchestrates the pipeline
│   ├── ocr_worker.py            # OpenCV preprocessing + Tesseract OCR (coordinates only)
│   ├── parser_worker.py         # Question detection and answer mapping
│   ├── grader_worker.py         # MCQ + written grading logic
│   ├── reliability_worker.py    # Calculates handwriting reliability score
│   └── annotator_worker.py      # pymupdf annotation — word and region level
│
├── services/
│   ├── llm_service.py           # Abstracted LLM caller (Gemini / Groq / Ollama)
│   ├── storage_service.py       # Cloudflare R2 file operations
│   └── cache_service.py         # Answer caching to reduce API calls
│
└── utils/
    ├── pdf_utils.py             # PDF validation, coordinate helpers
    ├── image_utils.py           # OpenCV preprocessing helpers
    └── text_utils.py            # Fuzzy matching, word coordinate matching, question parsers
```

---

## Environment Variables Required

```
# LLM Provider — "gemini", "groq", or "ollama"
LLM_PROVIDER=gemini

# Gemini (Primary)
GEMINI_API_KEY=your_key_here

# Groq (Fallback)
GROQ_API_KEY=your_key_here

# Ollama (Local fallback — no key needed, just URL)
OLLAMA_BASE_URL=http://localhost:11434

# Cloudflare R2 Storage
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_key
R2_SECRET_ACCESS_KEY=your_secret
R2_BUCKET_NAME=grading-engine

# Redis
REDIS_URL=redis://localhost:6379

# Grading confidence threshold — below this, flag for teacher review
CONFIDENCE_THRESHOLD=0.75

# Handwriting reliability threshold — below this, flag for teacher review
RELIABILITY_THRESHOLD=60

# Fuzzy match threshold — minimum similarity to match a flagged word to OCR bounding box
FUZZY_MATCH_THRESHOLD=85

# File size limit in MB
MAX_FILE_SIZE_MB=20
```

---

## What This Engine Does Not Handle

- User authentication or authorization
- Student or teacher account management
- Assignment creation or scheduling
- Email or push notifications
- The submission popup UI (platform's responsibility)
- Frontend UI of any kind
- Database of users or grades (returns results directly, main platform stores them)

All of the above are the responsibility of the main edtech platform.

---

## Project Taskmaster

A complete breakdown of every task in this project, in the exact order they must be built. Each task has a clear goal, what done looks like, and what it unlocks next. Nothing gets marked done until it works end to end.

---

### PHASE 1 — Core Pipeline

---

**TASK 1 — Project Setup**
Set up the project folder structure, Python virtual environment, and install all dependencies.

What done looks like:
- Folder structure matches the one defined in this document
- Virtual environment is active
- All libraries from requirements.txt install without errors on Mac M1
- `.env` file exists with placeholder values
- `.env.example` committed to git, `.env` in `.gitignore`

Unlocks: Everything. Nothing else can start until this is done.

---

**TASK 2 — PDF Validation and Type Detection**
Write a function that accepts a PDF file, checks it is valid, and determines whether it is typed or handwritten.

What done looks like:
- Rejects corrupted PDFs with a clear error message
- Rejects password-protected PDFs with a clear error message
- Rejects files over 20MB with a clear error message
- Rejects non-PDF files with a clear error message
- Returns "typed" or "handwritten" for valid PDFs
- Tested with at least one typed PDF and one handwritten scanned PDF

Unlocks: Task 3 and Task 4 (both depend on knowing the PDF type).

---

**TASK 3 — PDF to Images Conversion**
Convert every page of the PDF into a high-resolution image using pdf2image.

What done looks like:
- Each page of a multi-page PDF becomes a separate PNG image
- Images are stored temporarily in memory or a temp folder
- Resolution is high enough for OCR to work accurately (300 DPI minimum)
- Tested with a 3+ page PDF

Unlocks: Task 4 (OCR needs images), Task 7 (Gemini vision needs images).

---

**TASK 4 — OpenCV Preprocessing**
Clean up each page image before OCR to maximise Tesseract's bounding box accuracy.

What done looks like:
- Converts image to grayscale
- Applies contrast enhancement
- Removes noise
- Deskews tilted scans
- Output image is visibly cleaner than input when compared side by side
- Tested with a poorly lit, slightly tilted phone camera scan

Unlocks: Task 5 (Tesseract needs cleaned images).

---

**TASK 5 — Tesseract OCR (Bounding Boxes + Reliability Score)**
Run Tesseract on cleaned images to extract word bounding box coordinates and per-word confidence scores. Text accuracy does not matter here — only coordinates and confidence matter.

What done looks like:
- Returns a map of every detected word to its (x, y, width, height) on the page
- Returns a per-word confidence score for every word
- Calculates average confidence across the whole submission → reliability score
- Correctly labels reliability as high / medium / low based on thresholds
- Tested with both neat and messy handwriting samples

Unlocks: Task 9 (word coordinate matching needs this output), Task 10 (reliability score needed for annotation).

---

**TASK 6 — pdfplumber Extraction (Typed PDFs)**
For typed PDFs, extract exact word text and coordinates using pdfplumber.

What done looks like:
- Returns every word on the page with its exact (x, y, width, height)
- Accuracy is perfect — these are vector coordinates, not OCR guesses
- Tested with a typed PDF containing at least two questions and answers

Unlocks: Task 9 (typed PDF word coordinates feed into annotation), Task 8 (question parser needs text).

---

**TASK 7 — Question Parser**
Detect question boundaries in the extracted text and map each answer block to its question number.

What done looks like:
- Correctly identifies Q1, Q2, Q3 style labels
- Correctly identifies 1. 2. 3. and 1) 2) 3) style labels
- Groups the text between two question markers as the answer to the first question
- Returns a structured map: question number → answer text → page number → approximate region coordinates
- Tested with a mixed MCQ and written assignment
- Handles the case where a student skips a question (blank answer)

Unlocks: Task 8 (grader needs question-answer pairs), Task 9 (annotator needs question regions).

---

**TASK 8 — MCQ Grading**
Grade multiple choice and fill-in-the-blank answers using fuzzy string matching.

What done looks like:
- Correctly matches "B", "b", "option b", "option B" all to the answer "B"
- Handles minor OCR errors (e.g. "8" instead of "B") via fuzzy matching
- Returns score (full marks or zero) and feedback ("Correct" or "Incorrect — answer was B")
- No API call involved — purely local matching
- Tested with at least 5 MCQ answers including some with OCR noise

Unlocks: Task 10 (annotation needs MCQ scores), Task 11 (full grading result needs MCQ scores).

---

**TASK 9 — LLM Service Abstraction Layer**
Build the provider-agnostic LLM service that calls Gemini, Groq, or Ollama based on environment config, and automatically falls back if a provider fails.

What done looks like:
- Single function `grade_answer()` that works identically regardless of provider
- Reads `LLM_PROVIDER` from `.env` to decide which provider to use
- If Gemini returns a rate limit error, automatically retries with Groq
- If Groq fails, automatically retries with Ollama
- All fallback events are logged
- Returns consistent JSON regardless of which provider responded
- Tested by temporarily setting wrong API key to force fallback

Unlocks: Task 10 (written grading uses this service).

---

**TASK 10 — Written Answer Grading (Gemini Vision + Text)**
Grade written and descriptive answers using the LLM service. For handwritten PDFs, send the page image to Gemini. For typed PDFs or fallback providers, send extracted text.

What done looks like:
- Sends correct prompt including question, answer key, rubric, and student answer
- Receives structured JSON response with score, feedback, confidence, spelling_mistakes, correct_parts, wrong_parts
- Handles malformed JSON response — retries once then falls back to next provider
- Correctly uses image input for Gemini on handwritten PDFs
- Correctly uses text input for Groq and Ollama fallback
- Tested with at least 3 different written answers — one good, one partial, one wrong

Unlocks: Task 11 (word coordinate matching needs flagged words from this), Task 12 (annotation needs grading results).

---

**TASK 11 — Word Coordinate Matching**
Match each word flagged by Gemini (spelling mistakes, wrong phrases, correct phrases) to the bounding box coordinates returned by Tesseract or pdfplumber.

What done looks like:
- For each word in `spelling_mistakes`, `wrong_parts`, `correct_parts` from Gemini
- Searches Tesseract/pdfplumber bounding box map using rapidfuzz
- If similarity >= FUZZY_MATCH_THRESHOLD → returns the matched coordinates
- If no match found → returns None (region-level fallback will be used)
- Returns a final annotation map: each flagged item → coordinates (or None) → annotation type
- Tested with both neat handwriting (high match rate) and messy handwriting (low match rate)

Unlocks: Task 12 (annotator uses this map to place marks).

---

**TASK 12 — pymupdf PDF Annotation**
Open the original PDF and place all teacher-style annotations at the correct positions using the annotation map from Task 11.

What done looks like:
- Green highlight over correct sections (word or region level)
- Red strikethrough over wrong sections (word or region level)
- Red circle around spelling mistakes (word or region level)
- Score badge placed to the right of each answer region
- Sticky note with feedback text placed below each answer region
- Tick or cross per question depending on score
- Reliability stamp on page 1 (for handwritten submissions)
- Summary page appended at end with total score, grade, reliability level, per-question breakdown
- Original PDF untouched — output is a new file
- Tested with a full multi-question submission and verified visually

Unlocks: Task 13 (API needs the annotated PDF to return to the platform).

---

**TASK 13 — FastAPI Endpoints (Synchronous)**
Wire everything together into the two REST endpoints. At this stage grading happens synchronously inside the request — no async queue yet.

What done looks like:
- `POST /grade` accepts PDF file + answer key JSON, runs full pipeline, returns job result directly
- `GET /result/{job_id}` returns the stored result for a completed job
- Both endpoints return correct JSON matching the schema in this document
- Tested end to end with Postman or curl — submit a PDF, get back a graded PDF URL and scores
- Handles all error cases (corrupted PDF, wrong format, missing answer key) with clean error responses

Unlocks: Phase 2. The core engine works end to end at this point.

---

### PHASE 2 — Production Hardening

---

**TASK 14 — Celery + Redis Async Job Queue**
Move grading out of the HTTP request and into a background Celery worker. `POST /grade` now returns immediately with a job ID. Grading happens in the background.

What done looks like:
- `POST /grade` returns job_id and status "processing" instantly
- Grading pipeline runs as a Celery background task
- Job status stored in Redis and updated as pipeline progresses
- `GET /result/{job_id}` reads from Redis and returns current status
- Tested by submitting a job and polling status every 3 seconds until "graded"

Unlocks: Task 15 (fallbacks work better with async), real production readiness.

---

**TASK 15 — Groq Fallback**
Add Groq as automatic fallback in the LLM service when Gemini hits rate limits.

What done looks like:
- Gemini rate limit error automatically triggers Groq
- Groq uses extracted text (not image) for handwritten PDFs
- Fallback is logged clearly
- Tested by temporarily exhausting Gemini free tier quota

Unlocks: Task 16.

---

**TASK 16 — Ollama Local Fallback**
Add Ollama as the last-resort fallback when both Gemini and Groq are unavailable.

What done looks like:
- Groq failure automatically triggers Ollama
- Ollama runs locally and works with no internet connection
- Tested by disabling internet and verifying grading still works via Ollama

Unlocks: Task 17.

---

**TASK 17 — Confidence and Reliability Flagging**
Implement automatic flagging logic for teacher review based on grading confidence and handwriting reliability.

What done looks like:
- Questions below CONFIDENCE_THRESHOLD flagged individually
- Submissions with reliability below RELIABILITY_THRESHOLD flagged overall
- Status returns "review_needed" with a clear reason string
- Tested by submitting a very messy handwritten PDF and verifying it gets flagged

Unlocks: Task 18.

---

**TASK 18 — Answer Caching**
Cache graded answers so identical or near-identical student answers don't trigger a new API call.

What done looks like:
- First time an answer is graded, result is cached in Redis with a hash key
- Second time the same or very similar answer appears, cached result is returned instantly
- Cache key is based on question ID + fuzzy hash of student answer
- Tested by submitting two identical answers and confirming only one API call is made

Unlocks: Task 19.

---

**TASK 19 — Cloudflare R2 Storage**
Replace temporary local file storage with Cloudflare R2 for both original and graded PDFs.

What done looks like:
- Original PDF uploaded to R2 on submission
- Graded PDF uploaded to R2 after annotation
- URLs returned in API response are real R2 URLs accessible from a browser
- Local temp files cleaned up after upload
- Tested by downloading the returned URL and verifying it opens correctly

Unlocks: Task 20.

---

**TASK 20 — Full Error Handling**
Harden every failure point in the pipeline with proper error catching, logging, and clean API error responses.

What done looks like:
- Every known failure mode returns a clean JSON error response (not a 500 crash)
- All errors logged with enough detail to debug
- Celery job marked as "failed" on unrecoverable errors
- Tested by deliberately triggering each failure mode and verifying clean response

Unlocks: Task 21.

---

**TASK 21 — Docker + Docker Compose**
Containerise the entire engine so it runs identically on any machine or server.

What done looks like:
- `docker-compose up` starts FastAPI, Celery worker, and Redis together
- Full pipeline works inside Docker — no "works on my machine" issues
- Tested by running the full end-to-end flow inside Docker from scratch
- All environment variables passed via `.env` file

Unlocks: The project is complete and ready for integration with the main platform.

---

### DONE — Definition of Project Complete

The project is complete when:
- A typed PDF submission grades end to end and returns an annotated PDF via the API
- A handwritten PDF submission grades end to end with reliability score and word-level markup
- All three LLM providers work and fallback is tested
- All error cases return clean responses
- Everything runs inside Docker
- The two API endpoints are documented and stable enough for the platform team to integrate against

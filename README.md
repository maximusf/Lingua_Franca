# SmartRoute

# Teammates: Emmanuel, Chance, Maximus, Myra, Preston

https://youtu.be/TQBhUMrMmLc

**GridStorm Hacks 2026 @ UofSC**

SmartRoute is a document understanding and routing system built for utility inspection workflows. Upload an inspection email screenshot, an Excel release sheet, or a PDF report — SmartRoute extracts the key fields, scores its own confidence, and routes the record to the right team automatically.

Built for operations teams who currently read these documents manually, figure out what happened, and decide where to send them. SmartRoute does that in seconds.

## How It Works

```text
Upload file (.xlsx, .png, .jpg, .pdf)
    |
    v
Convert to text (OCR / Excel parsing / PDF extraction)
    |
    v
LLM extracts structured fields (permit #, result, address, etc.)
    |
    v
Validate, normalize, and score confidence
    |
    v
Route to the right team based on urgency rules
    |
    v
Display results with human review override when needed
```

The user uploads one or more files through the Streamlit UI. Each file is converted to text, sent through the extraction pipeline, and displayed as a structured record with urgency level, routing destination, and confidence score. If confidence is low or critical fields are missing, the system flags the record for human review and lets the user override the routing.

## The Problem

Inspection records arrive in inconsistent formats — email screenshots, Excel exports, PDFs, scanned forms. Someone has to read each one, figure out the permit number, whether it passed or failed, what type of inspection it was, and then decide which team handles it next. That process is slow, error-prone, and doesn't scale.

## Why This Approach

We considered sentiment analysis (VADER), but inspection records are operational documents, not opinion text. A sentiment score can't tell you whether an inspection should go to scheduling vs. the safety team.

We also considered training a custom NLP model, but that requires labeled training data and infrastructure that isn't realistic for a hackathon.

Instead, we use a local LLM (Mistral via Ollama) for field extraction paired with deterministic routing rules. This gives us:

- No paid API keys or cloud dependency
- Fast iteration on prompt quality
- Reliable extraction using a structured key-value format
- Rule-based routing that's transparent and auditable

We tested `phi3:mini` and `phi3` but Mistral performed better on our extraction task — more consistent field output in a parseable format.

## Tech Stack

| Component | Tool |
|-----------|------|
| Frontend | Streamlit |
| LLM | Ollama + Mistral (local) |
| Schema validation | Pydantic v2 |
| OCR | Tesseract + OpenCV preprocessing |
| Excel parsing | openpyxl |
| PDF extraction | pypdf |
| Image handling | Pillow |

## Pipeline Breakdown

**`backend/extract_to_txt.py`** — Converts uploaded files to plain text. Images go through OpenCV preprocessing (upscale 2x, grayscale, Otsu threshold) before Tesseract OCR for better text quality.

**`backend/extractor.py`** — Sends text to Ollama and parses the LLM response into structured fields. Uses a key-value prompt format that's more reliable than asking small models for JSON.

**`backend/validator.py`** — Normalizes results (e.g., "pass" -> PASS, "released" -> RELEASED), classifies permit categories, computes a confidence score based on field completeness, and flags records for human review.

**`backend/urgency.py`** — Applies deterministic routing rules. Gas inspections go to the safety team. Electrical releases go to field ops. Failed inspections go to human review. Routine passes go to scheduling.

**`backend/schema.py`** — Pydantic models shared across the pipeline (`LLMExtraction`, `InspectionRecord`).

## Evaluation

SmartRoute includes a synthetic test harness for measuring pipeline accuracy. Test records go through the same Ollama pipeline as real uploads — extraction, validation, and routing — then get compared against known ground truth.

### 1. Generate test data

```bash
python tests/generate_test_data.py --count 25     # 25, 50, or 100 records
```

Creates realistic inspection documents across 6 template styles (county emails, eTRAKiT forms, PDF reports, spreadsheets, etc.) with file types spread across PNG, JPG, JPEG, PDF, and XLSX. About 20% include simulated OCR noise and 15% have missing critical fields. Ground truth is saved to `data/synthetic/ground_truth.json`.

### 2. Run evaluation

```bash
python tests/evaluate.py --label "baseline"
```

Sends every test record through the full pipeline (Ollama must be running) and compares output to ground truth. The `--label` flag tags the run so you can track changes over time. Outputs:

- `data/synthetic/metrics.json` — per-field accuracy, routing accuracy, accuracy by file type, human review precision/recall, confidence calibration
- `data/synthetic/results.json` — detailed per-record comparison (expected vs. actual for every field)
- `data/synthetic/history.json` — appended after each run, stores a snapshot of key metrics with the label and timestamp

### 3. Generate charts

```bash
python tests/visualize.py
```

Reads `metrics.json` and `history.json` and produces PNG charts in `data/synthetic/charts/`:

- **Accuracy by file type** — bar chart comparing extraction and routing accuracy across PNG, JPG, PDF, XLSX
- **Per-field accuracy** — horizontal bar chart showing which extracted fields are strongest/weakest, color-coded by performance tier
- **Accuracy over iterations** — line chart tracking improvement across labeled runs (needs 2+ evaluation runs to be useful; with a single run it just shows one data point)

### 4. Clean up

```bash
python tests/generate_test_data.py --clean
```

Deletes all generated test data, results, metrics, and charts.

## Repository Structure

```text
SmartRoute/
├── app.py                          # Streamlit frontend (main entry point)
├── requirements.txt
├── backend/
│   ├── app.py                      # Backend pipeline test harness
│   ├── extract_to_txt.py           # File-to-text conversion (OCR, Excel, PDF)
│   ├── extractor.py                # LLM field extraction via Ollama
│   ├── validator.py                # Normalization, confidence scoring, review flags
│   ├── urgency.py                  # Deterministic routing rules
│   └── schema.py                   # Pydantic models
├── tests/
│   ├── generate_test_data.py       # Synthetic test data generator
│   ├── evaluate.py                 # Pipeline accuracy evaluation
│   └── visualize.py                # Matplotlib chart generation
├── data/
│   ├── samples/                    # Uploaded files
│   ├── processed_text/             # Converted .txt files
│   └── synthetic/                  # Test data and metrics
├── prompts/
│   └── extraction.txt
└── docs/
    └── frontend-spec.md
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Tesseract must be installed on the system for image OCR:

```bash
# Ubuntu/Debian
sudo apt install tesseract-ocr

# macOS
brew install tesseract

# Windows — install from https://github.com/tesseract-ocr/tesseract
```

## Running

**1. Start Ollama**

```bash
ollama serve
ollama pull mistral    # first time only
```

**2. Launch the app**

```bash
streamlit run app.py
```

**3. (Optional) Run the backend test harness**

```bash
streamlit run backend/app.py
```

**4. (Optional) Batch convert files from the command line**

```bash
python backend/extract_to_txt.py data/samples --out data/processed_text
```

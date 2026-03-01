# SmartRoute
Challenge for GridStorm Hacks 2026 @ UofSC

SmartRoute is a Python-based document understanding and routing system for utility inspection records. It takes messy inputs such as raw inspector notes, uploaded images, and Excel exports, converts them into usable text, extracts structured fields, scores confidence, and routes the result to the right downstream team.

## Tech Stack

- Python
- Streamlit
- Ollama
- Mistral
- Pydantic
- openpyxl
- PyTesseract
- Pillow
- pypdf

## The Problem

Inspection-related information does not arrive in one clean format. Teams may receive:

- raw text copied from emails or internal notes
- screenshots or image-based messages
- Excel exports with important values spread across cells
- PDFs and other semi-structured documents

That makes routing slow and inconsistent. Someone often has to read the document, figure out what happened, identify the permit or inspection type, determine whether it passed or failed, and then decide where it should go next.

## Our Proposed Solution

SmartRoute standardizes this process in Python.

At a high level, the system:

1. accepts text or uploaded files
2. converts files into machine-readable text when needed
3. sends the text to a local LLM for field extraction
4. validates and normalizes the extracted fields
5. applies deterministic routing and urgency rules
6. returns a structured record to the frontend

For raw text inputs, the project is currently averaging about 90% confidence across extracted records, based on the confidence scoring logic in the validation layer and our test iterations on sample inspection-style inputs.

## Why We Chose This Approach

Early on, we considered sentiment analysis, including VADER, but the project data is not really a sentiment problem. These inspection records are operational documents, not opinion-heavy user text. What matters is extracting factual fields such as permit number, inspection type, result, address, and contact details. A sentiment score would not reliably tell us whether an inspection should be routed to scheduling, field operations, or human review.

We also discussed training or fine-tuning an NLP model from scratch, but that was not realistic for the time constraints of a hackathon and would have required more labeled data, more ML infrastructure, and more model-training experience than was practical for this build.

So we settled on using Ollama with Mistral because it gave us the best balance of:

- local/offline execution
- no paid API dependency
- fast iteration during development
- stronger extraction quality on our document style

We tested `phi3:mini` and `phi3`, but they did not perform as well as Mistral on our extraction task. Mistral was more consistent at returning the fields we needed in a format we could parse and validate.

## Prompt Iteration

Prompt quality ended up mattering a lot.

We improved extraction by iterating on:

- stricter field instructions
- explicit allowed values for `result`
- requiring every field to appear exactly once
- forcing nulls instead of freeform commentary
- moving from looser output expectations toward a predictable key-value format

That iteration reduced noisy responses and made parsing more reliable. In practice, the extractor performs best when the model is told exactly which fields to output and how to represent missing values.

## How Data Flows Through the Project

### End-to-End Flow

```text
Frontend input
    ↓
Text parser / OCR layer
    ↓
LLM extraction
    ↓
Validation and normalization
    ↓
Urgency and routing rules
    ↓
Structured JSON returned to the frontend
```

### Current Repository Flows

There are currently two app entrypoints in the repo.

#### 1. Root `app.py`

This Streamlit app is the document ingestion and conversion flow.

```text
User uploads .xlsx / .jpg / .png / .pdf
    ↓
Files are saved into `data/samples/`
    ↓
`backend/extract_to_txt.py` converts each file into text
    ↓
Output `.txt` files are written into `data/processed_text/`
    ↓
Frontend displays extraction status
```

This flow currently handles:

- Excel files with `openpyxl`
- images with OCR through `pytesseract`
- PDFs with `pypdf`

For Excel, the project uses `openpyxl` to read raw cell contents sheet by sheet and flatten them into text. If you meant "pyxel", the actual library in the codebase is `openpyxl`.

For images, the project uses `pytesseract` with OCR to extract machine-readable text from `.png`, `.jpg`, and `.jpeg` inputs.

#### 2. `backend/app.py`

This Streamlit app is the structured extraction pipeline test harness.

```text
User provides raw text, `.xlsx`, or image
    ↓
Input is converted into raw text
    ↓
`backend/extractor.py` sends text to Ollama using Mistral
    ↓
`backend/validator.py` normalizes and scores the result
    ↓
`backend/urgency.py` assigns urgency and routing
    ↓
Structured record is displayed in the frontend
```

This is the flow that best represents the intended SmartRoute pipeline today.

## Backend Pipeline Breakdown

### `backend/extract_to_txt.py`

Responsible for file-to-text conversion.

- `dump_xlsx_to_txt()` reads Excel workbooks and writes text files
- `dump_image_to_txt()` runs OCR on image files
- `dump_pdf_to_txt()` extracts text from PDFs

### `backend/extractor.py`

Responsible for LLM-based field extraction.

- sends raw text to Ollama
- uses the `mistral` model
- expects a consistent key-value response
- parses the response into a typed extraction object

### `backend/validator.py`

Responsible for validation and normalization.

- normalizes results such as `pass`, `approved`, or `fail`
- classifies permit categories
- computes confidence score
- flags records for human review when needed

### `backend/urgency.py`

Responsible for deterministic routing logic.

- applies urgency rules
- maps records to destinations such as `field_ops`, `scheduling`, or `human_review`

### `backend/schema.py`

Defines the shared Pydantic models used throughout the system.

## Repository Structure

```text
SmartRoute/
├── README.md
├── LICENSE
├── requirements.txt
├── app.py
├── backend/
│   ├── app.py
│   ├── extract_to_txt.py
│   ├── extractor.py
│   ├── validator.py
│   ├── urgency.py
│   └── schema.py
├── prompts/
│   └── extraction.txt
├── docs/
│   └── frontend-spec.md
└── data/
    ├── samples/
    └── processed_text/
```

## What Is Working Now

- raw text can be passed through the structured extraction pipeline
- images can be converted to text with OCR
- Excel files can be converted to text from worksheet cell contents
- PDFs can be converted to text in the conversion flow
- extracted records are validated, scored, and routed

## Current Limitations

- the root `app.py` conversion flow is not fully wired into the structured backend pipeline yet
- the root frontend still contains placeholder JSON for some display sections
- PDF support exists in the conversion layer, but not yet in the structured Streamlit pipeline UI

## Installation

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

## Running the Project

### 1. Start Ollama

```bash
ollama serve
```

In another terminal, pull Mistral if you do not already have it:

```bash
ollama pull mistral
```

### 2. Run the frontend conversion app

```bash
python -m streamlit run app.py
```

### 3. Run the backend pipeline app

```bash
python -m streamlit run backend/app.py
```

### 4. Optional: run the batch text extraction script directly

```bash
python backend/extract_to_txt.py data/samples --out data/processed_text
```

## Summary

SmartRoute is a Python hackathon project focused on turning messy inspection documents into structured operational records. Instead of using sentiment analysis or attempting to build a custom NLP model from scratch, the project uses local LLM extraction with Ollama and Mistral, paired with OCR, Excel parsing, validation, and deterministic routing rules. The result is a practical pipeline that works well on raw text today and can be extended into a single unified frontend/backend flow.

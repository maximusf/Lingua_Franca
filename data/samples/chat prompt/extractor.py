"""
SmartRoute Extractor — Sends raw text to a local LLM via Ollama
and gets structured fields back using key-value extraction.

Pipeline position: raw text → extractor.py → LLMExtraction → validator.py
"""

import requests

from backend.schema import LLMExtraction

# Ollama runs locally — no API key, no internet needed
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"

# All fields the LLM should extract — used for parsing and as a fallback
_FIELD_NAMES = [
    "permit_number", "inspection_type", "result", "permit_category",
    "site_address", "county", "inspection_date", "description",
    "contact_name", "contact_phone", "contact_email", "inspector",
]

# Task prompt — key-value format is more reliable than JSON for small models.
# Each instruction is on its own line for clarity to the LLM.
# System context is baked into the opening line of the prompt since
# Ollama's /api/generate doesn't have a separate system role.
_EXTRACTION_PROMPT = """You are a precise data extraction system for utility inspection records.
Extract the following fields from the inspection document below.

Rules:
- Output each field on its own line in exact format:  field_name: value
- If a field is not found in the document, write ONLY the word null:  field_name: null
- NEVER add parenthetical notes like "(not provided)" — just write null
- For "result", normalize to one of: PASS, FAIL, APPROVED, REJECTED, PENDING, or null if unclear.
- Use the raw permit type string from the document for "permit_category" (e.g. "Residential", "Mobile Home").
- Every field must appear exactly once in your output.
- Do not add any fields, explanations, or commentary.

Fields:
permit_number: <permit or application number>
inspection_type: <type of inspection performed>
result: <PASS | FAIL | APPROVED | REJECTED | PENDING | null>
permit_category: <raw permit type from document>
site_address: <property address>
county: <county name>
inspection_date: <date of inspection>
description: <brief description or notes>
contact_name: <applicant or contact name>
contact_phone: <phone number>
contact_email: <email address>
inspector: <inspector name>

DOCUMENT TEXT:
<<<
{text}
>>>"""


def _build_prompt(raw_text: str) -> str:
    """Build the full extraction prompt with the document text inserted."""
    return _EXTRACTION_PROMPT.format(text=raw_text)


def _parse_kv_output(model_output: str) -> dict[str, str | None]:
    """Parse key: value lines from the LLM output into a dict.

    Uses split(":", 1) so values containing colons (addresses, etc.) are preserved.
    """
    fields = {name: None for name in _FIELD_NAMES}

    for line in model_output.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower().replace(" ", "_")
        value = value.strip()

        if key in fields:
            if value == "" or value.lower().startswith("null"):
                fields[key] = None
            else:
                fields[key] = value

    return fields


def extract_fields(raw_text: str) -> LLMExtraction:
    """Send raw text to Ollama and return a validated LLMExtraction.

    Uses key-value extraction format for reliability with small models.

    Handles:
      - Empty input → returns all-null LLMExtraction (skips LLM call)
      - Ollama not running → raises ConnectionError
      - All fields null → raises ValueError (extraction failed completely)
      - Schema validation failure → raises ValueError
    """
    if not raw_text or not raw_text.strip():
        return LLMExtraction()

    prompt = _build_prompt(raw_text)

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
        },
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
    except requests.ConnectionError:
        raise ConnectionError(
            f"Cannot connect to Ollama at {OLLAMA_URL}. "
            "Make sure Ollama is running: ollama serve"
        )

    model_output = response.json().get("response", "").strip()
    if not model_output:
        raise ValueError("LLM returned an empty response.")

    fields = _parse_kv_output(model_output)

    # Safety check — if LLM returned nothing useful, fail loudly
    if all(v is None for v in fields.values()):
        raise ValueError(
            f"Could not extract any fields from model output:\n{model_output[:500]}"
        )

    try:
        return LLMExtraction(**fields)
    except Exception as e:
        raise ValueError(
            f"Schema validation failed: {e}\nParsed fields: {fields}"
        )

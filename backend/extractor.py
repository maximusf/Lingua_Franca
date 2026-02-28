import requests
import json
from pathlib import Path
from typing import Dict, Any

# =========================
# Configuration
# =========================

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3:mini"  # Change if you pulled a different model
PROMPT_PATH = Path("prompts/extraction.txt")

REQUIRED_KEYS = {
    "document_type",
    "permit_id",
    "inspection_type",
    "result",
    "jurisdiction",
    "address",
    "inspection_date",
    "organization",
    "confidence_notes"
}

# =========================
# Prompt Loader
# =========================

def load_prompt(text: str) -> str:
    """
    Loads the extraction prompt template and injects document text.
    """
    if not PROMPT_PATH.exists():
        raise FileNotFoundError("Prompt file not found at prompts/extraction.txt")

    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.replace("{{TEXT}}", text)


# =========================
# Output Validation
# =========================

def validate_output(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures all required keys exist in the returned JSON.
    Missing keys are set to None.
    """
    for key in REQUIRED_KEYS:
        data.setdefault(key, None)

    # Optional: enforce uppercase normalization for result
    if data.get("result") and isinstance(data["result"], str):
        data["result"] = data["result"].upper()

    return data


# =========================
# Core Extraction Function
# =========================

def extract_fields(raw_text: str) -> Dict[str, Any]:
    """
    Sends document text to Ollama LLM and returns structured JSON.
    """

    if not raw_text or not raw_text.strip():
        raise ValueError("Empty document text provided")

    prompt = load_prompt(raw_text)

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0  # Critical for deterministic JSON output
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Ollama request failed: {e}")

    result_text = response.json().get("response", "").strip()

    if not result_text:
        raise ValueError("LLM returned empty response")

    try:
        parsed = json.loads(result_text)
    except json.JSONDecodeError:
        raise ValueError(
            f"LLM did not return valid JSON.\nRaw output:\n{result_text}"
        )

    return validate_output(parsed)
"""
SmartRoute Extractor — Sends raw text to Mistral via Ollama and gets structured fields back.

Pipeline position: raw text → extractor.py → LLMExtraction → validator.py
"""

import re
import json
import requests
from pathlib import Path

from backend.schema import LLMExtraction

# Ollama runs locally — no API key, no internet needed
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"

# Prompt template lives in a separate file so it can be tuned
# without touching Python code
PROMPT_PATH = Path("prompts/extraction.txt")


def load_prompt(text: str) -> str:
    """Load the prompt template and inject the document text."""
    template = PROMPT_PATH.read_text()
    return template.replace("{{TEXT}}", text)


def _strip_markdown(text: str) -> str:
    """Strip markdown code fences if the LLM wraps its JSON response in them.

    Mistral sometimes returns ```json ... ``` despite the prompt saying not to.
    This extracts just the JSON content from inside the fences.
    """
    # Match ```json ... ``` or ``` ... ``` (with optional language tag)
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def extract_fields(raw_text: str) -> LLMExtraction:
    """Send raw text to Ollama/Mistral and return a validated LLMExtraction.

    Handles edge cases:
      - Empty input → returns all-null LLMExtraction (skips LLM call)
      - Ollama not running → raises ConnectionError with helpful message
      - LLM wraps JSON in markdown → strips the fences before parsing
      - LLM returns invalid JSON → raises ValueError
    """
    # Edge case: empty or whitespace-only input — don't waste an LLM call
    if not raw_text or not raw_text.strip():
        return LLMExtraction()

    prompt = load_prompt(raw_text)

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0  # deterministic output for consistent extraction
        }
    }

    # Call Ollama — catch connection errors with a clear message
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
    except requests.ConnectionError:
        raise ConnectionError(
            f"Cannot connect to Ollama at {OLLAMA_URL}. "
            "Make sure Ollama is running: ollama serve"
        )

    result_text = response.json()["response"].strip()

    # Strip markdown fences if present (Mistral sometimes adds them)
    result_text = _strip_markdown(result_text)

    # Parse the JSON response
    try:
        data = json.loads(result_text)
    except json.JSONDecodeError:
        raise ValueError(
            f"LLM did not return valid JSON. Raw response:\n{result_text[:500]}"
        )

    # Convert to LLMExtraction — Pydantic ignores extra fields the LLM may add
    return LLMExtraction(**data)

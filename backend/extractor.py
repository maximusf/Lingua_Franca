import requests
import json
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"

PROMPT_PATH = Path("prompts/extraction.txt")

def load_prompt(text: str) -> str:
    template = PROMPT_PATH.read_text()
    return template.replace("{{TEXT}}", text)

def extract_fields(raw_text: str) -> dict:
    prompt = load_prompt(raw_text)

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0
        }
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=60)
    response.raise_for_status()

    result_text = response.json()["response"].strip()

    try:
        return json.loads(result_text)
    except json.JSONDecodeError:
        raise ValueError("LLM did not return valid JSON")

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

def validate_output(data: dict) -> dict:
    for key in REQUIRED_KEYS:
        data.setdefault(key, None)
    return data

parsed = json.loads(result_text)
return validate_output(parsed)
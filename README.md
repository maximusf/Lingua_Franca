# SmartRoute
Challenge for GridStorm Hacks 2026 @ UofSC

Converts messy inspector emails, texts, and portal exports into clean structured records with urgency scoring and automatic routing logic — built for Dominion Energy's field inspection workflow.

**100% free to run. No paid APIs. All Python.**

---

## How It Works

```
Raw Inspector Message
        ↓
  [LLM Extraction]     ← Ollama + Mistral (runs locally, free)
        ↓
  [Validation Layer]   ← Normalizes fields, catches bad LLM output
        ↓
  [Urgency Scoring]    ← Deterministic rules engine (1–5 scale)
        ↓
  [Routing Engine]     ← Maps urgency + permit type → correct team
        ↓
  Structured Record displayed in Streamlit dashboard
```

---

## Dependencies

### System Requirements
| Tool | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Entire stack — backend and UI |
| Git | any | Version control |
| Ollama | latest | Local LLM runner (free, no API key) |

### Python Packages (`requirements.txt`)
| Package | Version | Purpose |
|---|---|---|
| streamlit | >=1.40.0 | UI dashboard |
| pydantic | >=2.8.0 | Data validation and schema enforcement |
| requests | >=2.28.0 | HTTP client to talk to Ollama |
| openpyxl | >=3.1.0 | Excel file parsing (.xlsx) |

### LLM (runs locally via Ollama — no account or API key needed)
| Model | Size | Purpose |
|---|---|---|
| `mistral` | ~4.4 GB | Primary extraction model (Mistral 7B) |

---

## Quickstart

### 1. Clone the repo

```bash
git clone https://github.com/maximusf/SmartRoute.git
cd SmartRoute
```

### 2. Install Ollama and pull the model

```bash
# Install Ollama
# Linux/Mac:
curl -fsSL https://ollama.com/install.sh | sh
# Windows: download from https://ollama.com/download

# Pull the model (~4.4 GB — do this on good WiFi before the hackathon)
ollama pull mistral
```

Ollama runs at `http://localhost:11434` by default. No account or API key needed.

### 3. Set up Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # Linux/Mac
# .venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

### 4. Run the app

You need **two terminals**:

| Terminal | Command | What it does |
|---|---|---|
| 1 | `ollama serve` | Runs the local LLM |
| 2 | `source .venv/bin/activate && streamlit run app.py` | Runs the full app |

App opens automatically at `http://localhost:8501`

---

## Team Roles

| Role | File(s) | Owns |
|---|---|---|
| LLM Integration | `backend/extractor.py`, `prompts/extraction.txt` | Prompt design, Ollama connection, output parsing |
| Validation & Schema | `backend/schema.py`, `backend/validator.py` | Data models, normalization, review flags |
| Urgency & Routing | `backend/urgency.py` | Scoring logic, routing rules |
| UI | `app.py` | Streamlit dashboard, input/output display |
| Data & QA | `data/synthetic/` | 25+ test messages, edge cases, demo script |

---

## Demo Scenarios

Three pre-built scenarios load with one click in the UI:

1. **Routine Approval** — Dorchester County preliminary inspection, PASS → Scheduling, Low urgency
2. **Safety Hazard** — Gas test FAIL with detected leak → Safety Team, Critical urgency
3. **Ambiguous** — Forwarded email chain, unclear address → Human Review flag

---

## File Structure

```
SmartRoute/
├── README.md
├── .gitIgnore
├── requirements.txt          ← pip install -r requirements.txt
├── app.py                    ← Streamlit UI (entire frontend)
├── backend/
│   ├── schema.py             ← All Pydantic data models (4 enums + 2 models)
│   ├── extractor.py          ← Calls Ollama/Mistral, parses JSON response
│   ├── validator.py          ← Normalizes fields, scores confidence, triggers review flags
│   └── urgency.py            ← Urgency scoring + routing rules engine
├── prompts/
│   └── extraction.txt        ← LLM prompt template (12 fields, strict JSON output)
└── data/
    ├── samples/              ← Provided example emails (8 PNGs + 2 XLSX)
    └── synthetic/            ← Generated test messages
```

---

## Output Schema

Every processed message produces a record with these fields:

```json
{
  "incident_id": "uuid (auto-generated)",
  "timestamp": "ISO8601 (auto-generated)",
  "raw_input": "string (original message text)",

  "permit_number": "string | null",
  "inspection_type": "string | null",
  "result": "PASS | FAIL | APPROVED | REJECTED | PENDING | UNKNOWN",
  "permit_category": "residential | commercial | mobile_home | temp_power | accessory_structure | unknown",
  "site_address": "string | null",
  "county": "string | null",
  "inspection_date": "string | null",
  "description": "string | null",
  "contact_name": "string | null",
  "contact_phone": "string | null",
  "contact_email": "string | null",
  "inspector": "string | null",

  "urgency": "critical | high | medium | low",
  "urgency_score": "1-5",
  "routed_to": "field_ops | scheduling | safety_team | maintenance | human_review",
  "confidence_score": "0.0-1.0",
  "human_review_flag": "boolean",
  "review_reason": "string | null"
}
```

---

## Routing Rules

| Condition | Urgency | Score | Routed To |
|---|---|---|---|
| Gas/safety + FAIL | Critical | 5 | safety_team |
| Gas/safety (any result) | High | 4 | safety_team |
| Electrical release | High | 4 | field_ops |
| Missing/unknown result | Medium | 3 | human_review |
| Non-electrical FAIL | Medium | 3 | human_review |
| Mobile home pass | Low | 2 | scheduling |
| Routine pass/approval | Low | 1 | scheduling |

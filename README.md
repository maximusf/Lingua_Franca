# SmartRoute
Challenge for GridStorm Hacks 2026 @ UofSC

Converts messy inspector emails, texts, and portal exports into clean structured records with urgency scoring and automatic routing logic — built for Dominion Energy's field inspection workflow.

**100% free to run. No paid APIs. All Python.**

---

## How It Works

```
Raw Inspector Message
        ↓
  [LLM Extraction]     ← Ollama (llama3, runs locally, free)
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
| streamlit | 1.40.0 | UI dashboard |
| pydantic | 2.8.2 | Data validation and schema enforcement |
| httpx | 0.27.0 | HTTP client to talk to Ollama |
| python-dotenv | 1.0.1 | Load environment variables from .env |

### LLM (runs locally via Ollama — no account or API key needed)
| Model | Size | Purpose |
|---|---|---|
| `llama3` | ~4.7 GB | Primary extraction model |

---

## Quickstart

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/smartroute.git
cd smartroute
```

### 2. Install Ollama and pull the model

```bash
# Install Ollama (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the model (~4.7 GB — do this on good WiFi before the hackathon)
ollama pull llama3
```

Ollama runs at `http://localhost:11434` by default. No account or API key needed.

### 3. Set up Python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Run the app

You need **two terminals**:

| Terminal | Command | What it does |
|---|---|---|
| 1 | `ollama serve` | Runs the local LLM |
| 2 | `source venv/bin/activate && streamlit run app.py` | Runs the full app |

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
smartroute/
├── README.md
├── .gitignore
├── requirements.txt          ← pip install -r requirements.txt
├── app.py                    ← Streamlit UI (entire frontend)
├── backend/
│   ├── schema.py             ← All Pydantic data models
│   ├── extractor.py          ← Calls Ollama, parses JSON response
│   ├── validator.py          ← Normalizes fields, triggers review flags
│   └── urgency.py            ← Urgency scoring + routing logic
├── prompts/
│   └── extraction.txt        ← LLM prompt template (tune this)
└── data/
    ├── samples/              ← Provided example emails
    └── synthetic/            ← Generated test messages
```

---

## Output Schema

```json
{
  "incident_id": "uuid",
  "timestamp": "ISO8601",
  "raw_input": "string",
  "permit_number": "string | null",
  "inspection_type": "string | null",
  "result": "PASS | FAIL | APPROVED | PENDING | UNKNOWN",
  "permit_category": "residential | commercial | mobile_home | temp_power | accessory_structure | unknown",
  "address_raw": "string | null",
  "address_normalized": "string | null",
  "county": "string | null",
  "urgency": "critical | high | medium | low",
  "urgency_score": "1-5",
  "routed_to": "field_ops | scheduling | safety_team | maintenance | human_review",
  "confidence_score": "0.0-1.0",
  "human_review_flag": "boolean",
  "review_reason": "string | null"
}
```

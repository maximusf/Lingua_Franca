# SmartRoute
Challenge for GridStorm Hacks 2026 @ UofSC

Converts messy inspector emails, texts, and portal exports into clean structured records with urgency scoring and automatic routing logic — built for Dominion Energy's field inspection workflow.

**100% free to run. No paid APIs.**

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
  Structured Record displayed in React dashboard
```

---

## Dependencies

### System Requirements
| Tool | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Backend runtime |
| Node.js | v22.39.0 | Frontend runtime |
| npm | v10.8.2 | Frontend package manager |
| Git | any | Version control |
| Ollama | latest | Local LLM runner (free, no API key) |

### Python Packages (`backend/requirements.txt`)
| Package | Version | Purpose |
|---|---|---|
| fastapi | 0.115.0 | API framework |
| uvicorn | 0.30.6 | ASGI server to run FastAPI |
| pydantic | 2.8.2 | Data validation and schema enforcement |
| httpx | 0.27.0 | HTTP client to talk to Ollama |
| python-dotenv | 1.0.1 | Load environment variables from .env |

### Node Packages (`frontend/package.json`)
| Package | Version | Purpose |
|---|---|---|
| react | 18.3.1 | UI framework |
| react-dom | 18.3.1 | React DOM renderer |
| vite | 5.4.8 | Dev server and build tool |
| tailwindcss | 3.4.13 | Utility CSS styling |
| autoprefixer | 10.4.20 | CSS compatibility |
| postcss | 8.4.47 | CSS processing pipeline |

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

# Pull the model (downloads ~4.7 GB, do this on good WiFi)
ollama pull llama3

# Start the Ollama server (keep this running in its own terminal)
ollama serve
```

Ollama runs at `http://localhost:11434` by default. No key needed.

### 3. Set up the backend

```bash
cd backend

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# Start the API
uvicorn main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

### 4. Set up the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

App runs at: http://localhost:5173

### 5. You need three terminals running simultaneously

| Terminal | Command | What it does |
|---|---|---|
| 1 | `ollama serve` | Runs the local LLM |
| 2 | `cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000` | Runs the API |
| 3 | `cd frontend && npm run dev` | Runs the UI |

---

## Team Roles

| Role | File(s) | Owns |
|---|---|---|
| Backend Architect | `schema.py`, `validator.py`, `main.py` | Data models, validation rules, API routes |
| LLM Integration | `extractor.py`, `prompts/extraction.txt` | Prompt design, Ollama connection, output parsing |
| Urgency & Routing | `urgency.py` | Scoring logic, routing rules |
| Frontend | `frontend/src/` | React dashboard, UI components |
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
├── backend/
│   ├── requirements.txt
│   ├── main.py               ← FastAPI app (3 endpoints)
│   ├── schema.py             ← All Pydantic data models
│   ├── extractor.py          ← Calls Ollama, parses JSON response
│   ├── validator.py          ← Normalizes fields, triggers review flags
│   └── urgency.py            ← Urgency scoring + routing logic
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css
│       └── components/
│           ├── InputPanel.jsx    ← Text input + demo scenario buttons
│           ├── RecordCard.jsx    ← Structured output display
│           ├── RecordsTable.jsx  ← Session records table
│           └── StatsBar.jsx      ← Aggregate stats header
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

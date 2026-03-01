# SmartRoute Frontend Specification

## Overview

SmartRoute processes inspection emails/documents and automatically triages them by urgency, routing each to the right team. The frontend accepts input (raw text, Excel, or images), sends it through the backend pipeline, and displays structured results in a persistent, sortable dashboard.

---

## Input Section

### Input Methods (radio selector or tabs)
1. **Raw Text** — text area for pasting email content
2. **Excel (.xlsx)** — file uploader, each row = one inspection record
3. **Image (.png/.jpg)** — file uploader, uses OCR to extract text

### Controls
- **"Process" button** — runs the backend pipeline on the input
- **"Clear All" button** — resets the results table

### Behavior
- Results **accumulate** across multiple submissions (session-persistent)
- User can keep uploading files or pasting text without losing previous results
- Excel files with multiple rows should add one record per row to the results

---

## Output Section

### Summary Bar (top of results area)
Shows aggregate counts, updates after each submission.

Example: **"15 records processed — 1 Critical, 4 High, 8 Medium, 2 Low"**

Each count should be color-coded to match the urgency colors below.

---

### Results Table
All processed records displayed in a table, **sorted by urgency (most urgent first)**.

#### Table Columns

| Column | Description | Help Text (tooltip / ? button) |
|--------|-------------|-------------------------------|
| Urgency | Color-coded badge | "How time-sensitive this item is. Critical = immediate safety concern. High = needs action soon. Medium = needs review. Low = routine, no rush." |
| Permit # | Permit or application number | "The unique identifier for this inspection permit." |
| Inspection Type | What kind of inspection | "The type of inspection that was performed (e.g. Electrical Final, Gas Test, Temporary Power)." |
| Result | PASS, FAIL, APPROVED, etc. | "The outcome of the inspection. APPROVED/PASS means the inspection was successful. FAIL/REJECTED means it did not meet requirements." |
| Address | Site/property address | "The physical location where the inspection took place." |
| Routed To | Which team handles this | "The team this record has been automatically assigned to based on its content and urgency." |
| Data Quality | Complete / Partial / Incomplete | "How much information the system was able to extract from the document. Complete = all key fields found. Partial = some missing. Incomplete = too much missing, needs human review." |

#### Urgency Badges

| Level | Color | Label | Meaning |
|-------|-------|-------|---------|
| Critical | Red | CRITICAL | Safety hazard detected (e.g. failed gas inspection). Requires immediate attention. |
| High | Orange | HIGH | Needs action soon (e.g. electrical release waiting for field ops, or document too incomplete to process automatically). |
| Medium | Yellow | MEDIUM | Needs human review (e.g. inspection failed but not a safety issue, or result couldn't be determined). |
| Low | Green | LOW | Routine item (e.g. passed inspection, just needs to be filed/scheduled). No rush. |

#### Data Quality Badges

| Range | Color | Label | Meaning |
|-------|-------|-------|---------|
| 0.8 - 1.0 | Green | Complete | All key fields were found in the document. |
| 0.5 - 0.79 | Yellow | Partial | Some fields are missing. Review recommended. |
| Below 0.5 | Red | Incomplete | Too much information missing. Flagged for human review. |

#### Routing Destinations

| Destination | Help Text |
|-------------|-----------|
| Safety Team | "Gas leaks, safety hazards, or failed safety inspections. These need immediate human attention." |
| Field Ops | "Electrical releases and field work approvals. A contractor or crew may be waiting on this." |
| Scheduling | "Routine passed inspections that just need to be logged and scheduled. No action required." |
| Human Review | "The system couldn't confidently process this record. A person should review the original document." |

---

### Expandable Detail View
When a user clicks a row in the table, expand to show full details:

**Left side — Extracted Fields:**
- Permit Number
- Inspection Type
- Result
- Permit Category
- Site Address
- County
- Inspection Date
- Description
- Contact Name
- Contact Phone
- Contact Email
- Inspector

**Right side — Original Input:**
- The raw text that was submitted (so the user can compare what the system extracted vs. what was in the original document)

**Bottom — Routing Info:**
- Urgency level + score
- Routed to (team)
- Human review flag (yes/no)
- Review reason (if flagged) — e.g. "Missing permit number; Missing site address"

---

## Help / Info Buttons

Every column header and badge should have a **? icon** that shows a tooltip or popover with the help text listed above. This lets non-technical users understand what each field means without cluttering the UI.

---

## Backend Integration

The frontend calls these backend functions (all in the `backend/` package):

```python
from backend.extractor import extract_fields
from backend.validator import validate
from backend.urgency import apply_routing

# For file parsing:
# Excel: use openpyxl to read rows, concatenate cell values per row
# Images: use pytesseract + PIL to OCR

# Pipeline per record:
extraction = extract_fields(raw_text)      # returns LLMExtraction
record = validate(extraction, raw_text)     # returns InspectionRecord
record = apply_routing(record)              # returns InspectionRecord (enriched)

# Access results:
record.model_dump(mode="json")              # full record as dict
```

### Important Notes
- Ollama must be running locally (`ollama serve`) with the model pulled
- Model is configured in `backend/extractor.py` (currently `mistral`)
- Each LLM call takes 5-15 seconds depending on hardware
- For batch Excel processing, records should be processed sequentially (one LLM call at a time)
- Results are stored in Streamlit `session_state` — they persist within a session but not across browser refreshes

---

## File Structure Reference

```
SmartRoute/
  app.py                    # Main frontend (this is what gets built)
  backend/
    app.py                  # Backend test UI (already working)
    extractor.py            # LLM extraction
    validator.py            # Normalization + scoring
    urgency.py              # Routing rules
    schema.py               # All data models
  prompts/
    extraction.txt          # LLM prompt template (unused, prompt is now inline)
  data/
    samples/                # Test data (emails, xlsx files)
```

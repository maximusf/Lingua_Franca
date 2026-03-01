"""
SmartRoute CLI — Run the full backend pipeline from the command line.

Usage:
    python backend/app.py "raw inspection text here"
    echo "raw inspection text" | python backend/app.py

Pipeline: raw text → extractor → validator → urgency → JSON output
"""

import json
import sys
from pathlib import Path

# Add project root to path so `backend.*` imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.extractor import extract_fields
from backend.validator import validate
from backend.urgency import apply_routing


def main() -> None:
    # Get input text from argument or stdin
    if len(sys.argv) > 1:
        raw_text = " ".join(sys.argv[1:])
    elif not sys.stdin.isatty():
        raw_text = sys.stdin.read()
    else:
        print("Usage: python backend/app.py \"inspection text here\"")
        print("       echo \"inspection text\" | python backend/app.py")
        sys.exit(1)

    raw_text = raw_text.strip()
    if not raw_text:
        print("Error: empty input", file=sys.stderr)
        sys.exit(1)

    try:
        extraction = extract_fields(raw_text)
        record = validate(extraction, raw_text)
        record = apply_routing(record)
    except ConnectionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(record.model_dump(mode="json"), indent=2, default=str))


if __name__ == "__main__":
    main()

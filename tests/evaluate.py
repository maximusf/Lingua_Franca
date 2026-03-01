"""
SmartRoute Evaluation Script — Runs the full extraction pipeline on
synthetic test data and compares results to ground truth.

Produces per-record results, aggregate accuracy metrics, and
accuracy-by-file-type breakdowns. Each run is appended to a history
file so you can track accuracy improvements over time.

Usage: python tests/evaluate.py [--label "description of this run"]
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path so we can import backend modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.extractor import extract_fields
from backend.validator import validate
from backend.urgency import apply_routing

INPUT_DIR = PROJECT_ROOT / "data" / "synthetic" / "input"
TRUTH_PATH = PROJECT_ROOT / "data" / "synthetic" / "ground_truth.json"
RESULTS_PATH = PROJECT_ROOT / "data" / "synthetic" / "results.json"
METRICS_PATH = PROJECT_ROOT / "data" / "synthetic" / "metrics.json"
HISTORY_PATH = PROJECT_ROOT / "data" / "synthetic" / "history.json"


def normalize_for_compare(val):
    """Normalize a value for comparison (lowercase, strip whitespace)."""
    if val is None:
        return None
    return str(val).strip().lower()


def fields_match(extracted, expected, field):
    """Compare extracted vs expected for a given field.

    - None == None is a match (both missing)
    - For enum-like fields (result, permit_category, urgency, routed_to): exact match
    - For free text fields: case-insensitive contains check
    """
    ext = normalize_for_compare(extracted)
    exp = normalize_for_compare(expected)

    if ext is None and exp is None:
        return True
    if ext is None or exp is None:
        return False

    # For addresses, use contains (LLM may reformat slightly)
    if field in ("site_address", "contact_name", "contact_email"):
        # Check if the key parts match (street number + street name)
        return exp in ext or ext in exp

    return ext == exp


def _detect_file_type(raw_text):
    """Extract the source file type from the FILE: header line."""
    match = re.search(r"^FILE:\s*\S+\.(\w+)", raw_text, re.MULTILINE)
    if match:
        ext = match.group(1).lower()
        # Normalize jpeg -> jpg
        if ext == "jpeg":
            return "jpg"
        return ext
    return "unknown"


def evaluate_record(fname, raw_text, truth):
    """Run the pipeline on one record and compare to ground truth."""
    start = time.time()
    file_type = _detect_file_type(raw_text)

    try:
        llm_extraction = extract_fields(raw_text)
        validated = validate(llm_extraction, raw_text)
        routed = apply_routing(validated)
        record = routed.model_dump(mode="json")
        error = None
    except Exception as e:
        record = None
        error = str(e)

    elapsed = time.time() - start

    if record is None:
        return {
            "file": fname,
            "file_type": file_type,
            "error": error,
            "elapsed_s": round(elapsed, 2),
            "field_results": {},
        }

    # Compare each extraction field
    extraction_fields = [
        "permit_number", "inspection_type", "result", "permit_category",
        "site_address", "county", "inspection_date",
        "contact_name", "contact_phone", "contact_email", "inspector",
    ]

    field_results = {}
    for field in extraction_fields:
        expected = truth.get(field)
        extracted = record.get(field)
        match = fields_match(extracted, expected, field)
        field_results[field] = {
            "expected": expected,
            "extracted": extracted,
            "match": match,
        }

    # Compare routing fields
    routing_fields = {
        "urgency": "expected_urgency",
        "routed_to": "expected_routed_to",
    }
    for rec_field, truth_field in routing_fields.items():
        expected = truth.get(truth_field)
        extracted = record.get(rec_field)
        match = normalize_for_compare(extracted) == normalize_for_compare(expected)
        field_results[rec_field] = {
            "expected": expected,
            "extracted": extracted,
            "match": match,
        }

    # Human review flag
    expected_hr = truth.get("expected_human_review")
    extracted_hr = record.get("human_review_flag")
    field_results["human_review_flag"] = {
        "expected": expected_hr,
        "extracted": extracted_hr,
        "match": expected_hr == extracted_hr,
    }

    return {
        "file": fname,
        "file_type": file_type,
        "error": None,
        "elapsed_s": round(elapsed, 2),
        "confidence_score": record.get("confidence_score"),
        "field_results": field_results,
    }


def compute_metrics(all_results):
    """Compute aggregate accuracy metrics from per-record results."""
    total = len(all_results)
    errors = sum(1 for r in all_results if r["error"] is not None)
    successful = [r for r in all_results if r["error"] is None]

    if not successful:
        return {"total": total, "errors": errors, "note": "All records failed"}

    # Per-field accuracy
    all_fields = [
        "permit_number", "inspection_type", "result", "permit_category",
        "site_address", "county", "inspection_date",
        "contact_name", "contact_phone", "contact_email", "inspector",
        "urgency", "routed_to", "human_review_flag",
    ]

    field_accuracy = {}
    for field in all_fields:
        matches = sum(
            1 for r in successful
            if r["field_results"].get(field, {}).get("match", False)
        )
        field_accuracy[field] = {
            "correct": matches,
            "total": len(successful),
            "accuracy": round(matches / len(successful), 3),
        }

    # Overall extraction accuracy (all extraction fields correct)
    extraction_fields = [
        "permit_number", "inspection_type", "result", "permit_category",
        "site_address", "county", "inspection_date",
    ]
    perfect_extractions = sum(
        1 for r in successful
        if all(r["field_results"].get(f, {}).get("match", False) for f in extraction_fields)
    )

    # Routing accuracy (both urgency and routed_to correct)
    perfect_routing = sum(
        1 for r in successful
        if (r["field_results"].get("urgency", {}).get("match", False)
            and r["field_results"].get("routed_to", {}).get("match", False))
    )

    # Human review precision/recall
    hr_tp = sum(1 for r in successful
                if r["field_results"].get("human_review_flag", {}).get("expected") is True
                and r["field_results"].get("human_review_flag", {}).get("extracted") is True)
    hr_fp = sum(1 for r in successful
                if r["field_results"].get("human_review_flag", {}).get("expected") is False
                and r["field_results"].get("human_review_flag", {}).get("extracted") is True)
    hr_fn = sum(1 for r in successful
                if r["field_results"].get("human_review_flag", {}).get("expected") is True
                and r["field_results"].get("human_review_flag", {}).get("extracted") is False)

    hr_precision = round(hr_tp / (hr_tp + hr_fp), 3) if (hr_tp + hr_fp) > 0 else 0
    hr_recall = round(hr_tp / (hr_tp + hr_fn), 3) if (hr_tp + hr_fn) > 0 else 0

    # Average confidence for correct vs incorrect extractions
    correct_confidences = [
        r["confidence_score"] for r in successful
        if all(r["field_results"].get(f, {}).get("match", False) for f in extraction_fields)
        and r["confidence_score"] is not None
    ]
    incorrect_confidences = [
        r["confidence_score"] for r in successful
        if not all(r["field_results"].get(f, {}).get("match", False) for f in extraction_fields)
        and r["confidence_score"] is not None
    ]

    avg_conf_correct = round(sum(correct_confidences) / len(correct_confidences), 3) if correct_confidences else None
    avg_conf_incorrect = round(sum(incorrect_confidences) / len(incorrect_confidences), 3) if incorrect_confidences else None

    # Accuracy by file type
    file_types = sorted(set(r.get("file_type", "unknown") for r in successful))
    accuracy_by_file_type = {}
    for ft in file_types:
        ft_records = [r for r in successful if r.get("file_type") == ft]
        ft_perfect = sum(
            1 for r in ft_records
            if all(r["field_results"].get(f, {}).get("match", False) for f in extraction_fields)
        )
        ft_routing = sum(
            1 for r in ft_records
            if (r["field_results"].get("urgency", {}).get("match", False)
                and r["field_results"].get("routed_to", {}).get("match", False))
        )
        accuracy_by_file_type[ft] = {
            "count": len(ft_records),
            "extraction_accuracy": round(ft_perfect / len(ft_records), 3),
            "routing_accuracy": round(ft_routing / len(ft_records), 3),
        }

    # Timing
    total_time = sum(r["elapsed_s"] for r in all_results)
    avg_time = round(total_time / total, 2)

    return {
        "total_records": total,
        "errors": errors,
        "successful": len(successful),
        "field_accuracy": field_accuracy,
        "perfect_extraction_rate": round(perfect_extractions / len(successful), 3),
        "perfect_routing_rate": round(perfect_routing / len(successful), 3),
        "human_review_precision": hr_precision,
        "human_review_recall": hr_recall,
        "avg_confidence_correct": avg_conf_correct,
        "avg_confidence_incorrect": avg_conf_incorrect,
        "accuracy_by_file_type": accuracy_by_file_type,
        "total_time_s": round(total_time, 1),
        "avg_time_per_record_s": avg_time,
    }


def print_summary(metrics):
    """Print a readable summary table."""
    print("\n" + "=" * 60)
    print("SMARTROUTE EVALUATION RESULTS")
    print("=" * 60)

    print(f"\nRecords: {metrics['successful']}/{metrics['total_records']} successful "
          f"({metrics['errors']} errors)")
    print(f"Time: {metrics['total_time_s']}s total, {metrics['avg_time_per_record_s']}s avg")

    print(f"\nPerfect extraction rate: {metrics['perfect_extraction_rate']:.1%}")
    print(f"Perfect routing rate:    {metrics['perfect_routing_rate']:.1%}")

    print(f"\nHuman review precision: {metrics['human_review_precision']:.1%}")
    print(f"Human review recall:    {metrics['human_review_recall']:.1%}")

    if metrics.get("avg_confidence_correct") is not None:
        print(f"\nAvg confidence (correct):   {metrics['avg_confidence_correct']:.3f}")
    if metrics.get("avg_confidence_incorrect") is not None:
        print(f"Avg confidence (incorrect): {metrics['avg_confidence_incorrect']:.3f}")

    if metrics.get("accuracy_by_file_type"):
        print("\n--- Accuracy by File Type ---")
        print(f"{'Type':<10} {'Count':>6} {'Extraction':>12} {'Routing':>10}")
        print("-" * 40)
        for ft, stats in metrics["accuracy_by_file_type"].items():
            print(f"{ft:<10} {stats['count']:>6} {stats['extraction_accuracy']:>11.1%} {stats['routing_accuracy']:>9.1%}")

    print("\n--- Per-Field Accuracy ---")
    print(f"{'Field':<22} {'Correct':>8} {'Total':>6} {'Accuracy':>10}")
    print("-" * 48)
    for field, stats in metrics["field_accuracy"].items():
        acc = f"{stats['accuracy']:.1%}"
        print(f"{field:<22} {stats['correct']:>8} {stats['total']:>6} {acc:>10}")

    print("=" * 60)


def append_to_history(metrics, label):
    """Append this run's key metrics to history.json for tracking over time."""
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "label": label,
        "total_records": metrics["total_records"],
        "successful": metrics["successful"],
        "perfect_extraction_rate": metrics["perfect_extraction_rate"],
        "perfect_routing_rate": metrics["perfect_routing_rate"],
        "human_review_precision": metrics["human_review_precision"],
        "human_review_recall": metrics["human_review_recall"],
        "accuracy_by_file_type": metrics.get("accuracy_by_file_type", {}),
        "avg_time_per_record_s": metrics["avg_time_per_record_s"],
    }

    history = []
    if HISTORY_PATH.exists():
        history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))

    history.append(entry)
    HISTORY_PATH.write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"History:          {HISTORY_PATH} ({len(history)} runs)")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate SmartRoute extraction pipeline.")
    parser.add_argument("--label", type=str, default="",
                        help="Short label for this run (e.g. 'baseline', 'after prompt v2')")
    args = parser.parse_args()

    if not TRUTH_PATH.exists():
        print(f"Ground truth not found at {TRUTH_PATH}")
        print("Run: python tests/generate_test_data.py first")
        sys.exit(1)

    ground_truth = json.loads(TRUTH_PATH.read_text(encoding="utf-8"))
    txt_files = sorted(INPUT_DIR.glob("*.txt"))

    if not txt_files:
        print(f"No .txt files found in {INPUT_DIR}")
        sys.exit(1)

    print(f"Evaluating {len(txt_files)} files...")
    all_results = []

    for i, txt_path in enumerate(txt_files, 1):
        fname = txt_path.name
        truth = ground_truth.get(fname)
        if truth is None:
            print(f"  [{i}/{len(txt_files)}] {fname}: SKIPPED (no ground truth)")
            continue

        raw_text = txt_path.read_text(encoding="utf-8")
        result = evaluate_record(fname, raw_text, truth)
        all_results.append(result)

        status = "OK" if result["error"] is None else f"ERROR: {result['error'][:50]}"
        print(f"  [{i}/{len(txt_files)}] {fname}: {status} ({result['elapsed_s']}s)")

    # Compute and save metrics
    metrics = compute_metrics(all_results)

    RESULTS_PATH.write_text(json.dumps(all_results, indent=2, default=str), encoding="utf-8")
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    # Append to history for tracking over time
    append_to_history(metrics, args.label)

    print_summary(metrics)

    print(f"\nDetailed results: {RESULTS_PATH}")
    print(f"Metrics:          {METRICS_PATH}")


if __name__ == "__main__":
    main()

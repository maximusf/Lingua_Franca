"""
SmartRoute Test Data Generator — Creates synthetic inspection documents
with known ground truth for evaluating the extraction pipeline.

Generates ~120 .txt files in data/synthetic/input/ and a ground_truth.json.

Usage: python tests/generate_test_data.py
"""

import json
import random
from pathlib import Path

random.seed(42)  # reproducible

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic" / "input"
TRUTH_PATH = Path(__file__).resolve().parent.parent / "data" / "synthetic" / "ground_truth.json"

# --- Building blocks for synthetic data ---

COUNTIES = [
    "Richland", "Dorchester", "Aiken", "Charleston", "Berkeley",
    "Lexington", "Greenville", "Spartanburg", "York", "Horry",
]

STREETS = [
    "Oak Dr", "Main St", "Elm Ave", "Pine Rd", "Maple Ln",
    "Cedar Blvd", "Birch Way", "Walnut Ct", "Spruce Pl", "Ash Dr",
    "Magnolia Way", "Palmetto Rd", "Cypress Ln", "Hickory St", "Willow Ave",
]

CITIES = [
    "Columbia, SC 29223", "Summerville, SC 29483", "North Charleston, SC 29405",
    "Graniteville, SC 29829", "Mount Pleasant, SC 29464", "Lexington, SC 29072",
    "Greenville, SC 29601", "Spartanburg, SC 29301", "Rock Hill, SC 29730",
    "Myrtle Beach, SC 29577",
]

CONTACT_NAMES = [
    "HAVEN HOMES LLC", "GREAT SOUTHERN HOMES INC", "MURRAY ELECTRICAL SERVICES LLC",
    "TIMOTHY BARTON", "JOHN SMITH", "SMITH CONSTRUCTION CO",
    "JONES BUILDING LLC", "CAROLINA CONTRACTORS INC", "PATRIOT HOMES LLC",
    "BAKER ELECTRIC", "DELTA PLUMBING LLC", "SUNRISE BUILDERS",
    "QUALITY HOME SERVICES", "ALLSTATE CONSTRUCTION", "PALMETTO POWER CO",
]

INSPECTORS = [
    "K. Howard", "Todd Fetterhoff", "A. Johnson", "R. Martinez",
    "S. Williams", "J. Davis", "M. Brown", "L. Wilson",
    "T. Anderson", "P. Thomas", "D. Jackson", "C. White",
]

PHONE_NUMBERS = [
    "(803) 555-1234", "(843) 555-5678", "(864) 555-9012",
    "(803) 555-3456", "(843) 555-7890", "(864) 555-2345",
]

EMAILS = [
    "contact@havenhomessc.com", "info@greatsouthernhomes.com",
    "office@murrayelectric.com", "jsmith@gmail.com",
    "dispatch@carolinacontractors.com", "permits@bakerelectric.com",
]

DATE_FORMATS = [
    lambda m, d, y: f"{m}/{d}/{y}",             # 12/22/2025
    lambda m, d, y: f"{m}-{d}-{y}",             # 12-22-2025
    lambda m, d, y: f"{y}-{m:02d}-{d:02d}",     # 2025-12-22
    lambda m, d, y: f"December {d}, {y}",        # December 22, 2025
    lambda m, d, y: f"Monday, December {d}, {y}",  # Monday, December 22, 2025
]

# --- Document templates ---
# Each template is a function that takes field values and returns (text, ground_truth_dict)

PERMIT_PREFIXES = {
    "residential": ["RBD25-", "RES-", "R-"],
    "commercial": ["CBD25-", "COM-", "C-"],
    "mobile_home": ["MH25-", "MHP-"],
    "temp_power": ["REL25-", "2025-RELEC-", "TP-"],
    "accessory_structure": ["ACC25-", "AS-"],
}

INSPECTION_TYPES = {
    "residential": ["RES GAS TEST", "RES ELECTRIC", "RES FINAL", "RES FRAMING", "RES PLUMBING"],
    "commercial": ["COMM ELECTRIC", "COMM FIRE", "COMM FINAL", "COMM PLUMBING"],
    "mobile_home": ["Mobile Home First Inspection", "MH-PERMANENT SERVICE", "Mobile Home Final"],
    "temp_power": ["RES TEMP ELECTRIC", "REL TEMP ELECTRIC", "200 amp release", "TEMP POWER POLE"],
    "accessory_structure": ["Electric Preliminary", "RES ACCESSORY ELECTRIC", "ACCESSORY FINAL"],
}


def _gen_permit_number(category):
    prefix = random.choice(PERMIT_PREFIXES[category])
    num = random.randint(100, 99999)
    return f"{prefix}{num:05d}"


def _gen_address():
    num = random.randint(100, 9999)
    street = random.choice(STREETS)
    city = random.choice(CITIES)
    return f"{num} {street} {city}"


def _gen_date():
    m = random.randint(10, 12)
    d = random.randint(1, 28)
    y = 2025
    fmt = random.choice(DATE_FORMATS)
    return fmt(m, d, y)


def _garble(text):
    """Simulate OCR noise on a string."""
    if not text:
        return text
    chars = list(text)
    n_swaps = max(1, len(chars) // 3)
    for _ in range(n_swaps):
        i = random.randint(0, len(chars) - 1)
        chars[i] = random.choice("MNRSTIAOELGXK@#&")
    return "".join(chars)


# File extensions to simulate different input types
IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg"]


# --- Template: Richland County Inspection Result ---
def template_richland(fields):
    ext = random.choice(IMAGE_EXTENSIONS)
    return f"""FILE: synthetic_{fields['_id']}{ext}
================================================================================

Richland County

BUILDING INSPECTIONS Email: developmentservices@rcgov.us
2020 HAMPTON ST Phone: (803) 576-2140
COLUMBIA, SC 29202 Fax: (803) 576-2138
BUILDING INSPECTIONS RESULTS
Permit: {fields['permit_number']} APPLICANT: {fields['contact_name']}

Site Address: {fields['site_address']}

The following inspection(s) was completed and below is the result(s):
Inspection Type: {fields['inspection_type']} Inspection Date: {fields['inspection_date']}
Result: {fields['result']}
Remarks: eTRAKiT Inspection Request
Notes: {fields.get('notes', 'Residential Electrical Release')}

Contact Name: {fields['contact_name']}
Phone: {fields.get('contact_phone', '')}
e-Mail: {fields.get('contact_email', '')}

{fields.get('inspector', '')}
Inspector
"""


# --- Template: Dorchester County Email ---
def template_dorchester(fields):
    ext = random.choice(IMAGE_EXTENSIONS)
    return f"""FILE: synthetic_{fields['_id']}{ext}
================================================================================

From: <permits@evolveplanning.com>
Sent on: {fields['inspection_date']}
To: releases@sc.dominionenergyaccount.com
CC: inspections@dorchestercounty.net

Subject: [EXTERNAL] Dorchester County: Utility Release {fields['inspection_type']} Dominion

CAUTION! This message was NOT SENT from DOMINION ENERGY

Dorchester County {fields['inspection_type']} Inspection {fields['result'].lower()}.

Permit Number: {fields['permit_number']}
Permit Type: {fields.get('permit_type', 'Residential')}
Permit Category: {fields.get('raw_category', 'Residential')}
Address: {fields['site_address']}
Description: {fields.get('description_text', 'New construction')}
Inspector: {fields.get('inspector', '')}

Contact Name: {fields['contact_name']}
Contact Org: {fields['contact_name']}
Contact Phone: {fields.get('contact_phone', '')}
"""


# --- Template: eTRAKiT Inspection Form ---
def template_etrakit(fields):
    ext = random.choice(IMAGE_EXTENSIONS)
    return f"""FILE: synthetic_{fields['_id']}{ext}
================================================================================

Inspection - {fields['inspection_type']}

Inspection Type:    {fields['inspection_type']}
Order#:             {random.randint(0, 99999)}

Result:             {fields['result']}
Scheduled Date:     {fields['inspection_date']}
Completed Date:     {fields['inspection_date']}
Inspector:          {fields.get('inspector', '')}
Remarks:            eTRAKiT Inspection Request

Notes:

Contact Name: {fields['contact_name']}
Site Address: {fields['site_address']}
Phone: {fields.get('contact_phone', '')}
e-Mail: {fields.get('contact_email', '')}
"""


# --- Template: Mount Pleasant Release Email ---
def template_mt_pleasant(fields):
    ext = random.choice(IMAGE_EXTENSIONS)
    return f"""FILE: synthetic_{fields['_id']}{ext}
================================================================================

permits@tompsc.com {fields['inspection_date']}

ReleaseDesk

CAUTION! This message was NOT SENT from DOMINION ENERGY

Address: {fields['site_address']}

Subject: {fields['inspection_type']}
Type: {fields.get('raw_category', 'Residential')}

Permit: {fields['permit_number']}
Inspector: {fields.get('inspector', '')}

Permit Clerk
Mount Pleasant, SC 29464
Office (843) 884-9517
"""


# --- Template: Spreadsheet-style record ---
def template_spreadsheet(fields):
    return f"""FILE: synthetic_{fields['_id']}.xlsx
================================================================================

[SHEET] Sheet1
--------------------------------------------------------------------------------
\tMunicipality: {fields.get('county', 'Aiken')} County
Release Date\tPermit #\tAddress\t\t\t\tRelease Type\tStructure Type\tReason For Release
\t\tStreet #\tStreet Name/City\tLot/Unit\tSubdivision\tName
{fields['inspection_date']}\t{fields['permit_number']}\t{fields['site_address']}\t\t\t{fields['contact_name']}\tELEC\tPOLE\t{fields['result']}


"""


# --- Template: PDF Inspection Report ---
def template_pdf_report(fields):
    return f"""FILE: synthetic_{fields['_id']}.pdf
================================================================================

{fields.get('county', 'Richland')} County Building & Codes Department
INSPECTION REPORT

Date: {fields['inspection_date']}
Report Generated for Permit #{fields['permit_number']}

PROPERTY INFORMATION
  Address: {fields['site_address']}
  County: {fields.get('county', '')}

INSPECTION DETAILS
  Type: {fields['inspection_type']}
  Category: {fields.get('raw_category', 'Residential')}
  Result: {fields['result']}
  Inspector: {fields.get('inspector', '')}

APPLICANT INFORMATION
  Name: {fields['contact_name']}
  Phone: {fields.get('contact_phone', '')}
  Email: {fields.get('contact_email', '')}

This report is generated automatically. For questions, contact the Building & Codes Department.
"""


TEMPLATES = [
    template_richland,
    template_dorchester,
    template_etrakit,
    template_mt_pleasant,
    template_spreadsheet,
    template_pdf_report,
]

# Result values and their ground truth enum mappings
RESULTS = {
    "PASS": "PASS",
    "FAIL": "FAIL",
    "APPROVED": "APPROVED",
    "approved": "APPROVED",
    "REJECTED": "REJECTED",
    "RELEASED": "RELEASED",
    "PENDING": "PENDING",
}


def generate_record(record_id, category, result_raw, add_noise=False, drop_fields=None):
    """Generate a single synthetic record with ground truth."""
    drop_fields = drop_fields or []

    inspection_type = random.choice(INSPECTION_TYPES[category])
    permit_number = _gen_permit_number(category)
    site_address = _gen_address()
    county = random.choice(COUNTIES)
    inspection_date = _gen_date()
    contact_name = random.choice(CONTACT_NAMES)
    inspector = random.choice(INSPECTORS)
    contact_phone = random.choice(PHONE_NUMBERS)
    contact_email = random.choice(EMAILS)

    # Build ground truth
    truth = {
        "permit_number": permit_number,
        "inspection_type": inspection_type,
        "result": RESULTS[result_raw],
        "permit_category": category,
        "site_address": site_address,
        "county": county,
        "inspection_date": inspection_date,
        "contact_name": contact_name,
        "contact_phone": contact_phone,
        "contact_email": contact_email,
        "inspector": inspector,
    }

    # Fields for the template
    fields = {
        "_id": f"{record_id:03d}",
        "permit_number": permit_number,
        "inspection_type": inspection_type,
        "result": result_raw,
        "site_address": site_address,
        "county": county,
        "inspection_date": inspection_date,
        "contact_name": contact_name,
        "inspector": inspector,
        "contact_phone": contact_phone,
        "contact_email": contact_email,
        "raw_category": category.replace("_", " ").title(),
    }

    # Apply OCR noise to some fields
    if add_noise:
        for noise_field in ["contact_name", "contact_phone", "contact_email", "inspector"]:
            if noise_field not in drop_fields:
                fields[noise_field] = _garble(fields[noise_field])
                truth[noise_field] = None  # garbled = expect null

    # Drop fields (simulate missing data)
    for f in drop_fields:
        fields[f] = ""
        truth[f] = None

    # Pick a template
    template = random.choice(TEMPLATES)
    text = template(fields)

    # Compute expected routing (mirrors urgency.py logic)
    result_enum = RESULTS[result_raw]
    itype_lower = inspection_type.lower()

    # Determine expected routing
    is_gas = any(kw in itype_lower for kw in ["gas", "leak", "safety", "hazard"])
    is_electrical = any(kw in itype_lower for kw in [
        "electrical release", "temp electric", "temp power",
        "amp release", "perm power", "rel temp", "elec",
    ])

    if is_gas:
        if result_enum == "FAIL":
            truth["expected_urgency"] = "critical"
            truth["expected_routed_to"] = "safety_team"
        else:
            truth["expected_urgency"] = "high"
            truth["expected_routed_to"] = "safety_team"
    elif is_electrical:
        truth["expected_urgency"] = "high"
        truth["expected_routed_to"] = "field_ops"
    elif result_enum == "UNKNOWN":
        truth["expected_urgency"] = "medium"
        truth["expected_routed_to"] = "human_review"
    elif result_enum in ("FAIL", "REJECTED"):
        truth["expected_urgency"] = "medium"
        truth["expected_routed_to"] = "human_review"
    elif category == "mobile_home" and result_enum in ("PASS", "APPROVED", "RELEASED"):
        truth["expected_urgency"] = "low"
        truth["expected_routed_to"] = "scheduling"
    elif result_enum in ("PASS", "APPROVED", "RELEASED"):
        truth["expected_urgency"] = "low"
        truth["expected_routed_to"] = "scheduling"
    else:
        truth["expected_urgency"] = "medium"
        truth["expected_routed_to"] = "human_review"

    # Expected human review flag
    has_permit = truth["permit_number"] is not None
    has_address = truth["site_address"] is not None
    truth["expected_human_review"] = (
        not has_permit or not has_address or result_enum == "UNKNOWN"
    )

    return text, truth


def clean_synthetic_data():
    """Delete all generated synthetic data (input files, ground truth, results, metrics)."""
    import shutil
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
        print(f"Deleted {OUT_DIR}")
    for p in [TRUTH_PATH,
              TRUTH_PATH.parent / "results.json",
              TRUTH_PATH.parent / "metrics.json"]:
        if p.exists():
            p.unlink()
            print(f"Deleted {p}")
    print("Clean complete.")

# --- Main test dataset generation logic ---
# Generates a mix of clean, noisy, and incomplete records
# to thoroughly test the extraction pipeline's robustness and routing logic.
def generate_dataset(count):
    """Generate `count` synthetic records with proportional noise/missing splits.

    Breakdown:
      ~65% clean records (full coverage of categories x results)
      ~20% noisy records (OCR garble)
      ~15% missing critical fields
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    n_noisy = max(1, round(count * 0.20))
    n_missing = max(1, round(count * 0.15))
    n_clean = count - n_noisy - n_missing

    ground_truth = {}
    record_id = 1
    categories = list(INSPECTION_TYPES.keys())
    result_options = list(RESULTS.keys())

    # Clean records — cycle through category+result combos for coverage
    combos = [(cat, res) for cat in categories for res in result_options]
    for i in range(n_clean):
        category, result_raw = combos[i % len(combos)]
        text, truth = generate_record(record_id, category, result_raw)
        fname = f"synthetic_{record_id:03d}.txt"
        (OUT_DIR / fname).write_text(text, encoding="utf-8")
        ground_truth[fname] = truth
        record_id += 1

    # Noisy records (OCR garble)
    for _ in range(n_noisy):
        category = random.choice(categories)
        result_raw = random.choice(result_options)
        text, truth = generate_record(record_id, category, result_raw, add_noise=True)
        fname = f"synthetic_{record_id:03d}.txt"
        (OUT_DIR / fname).write_text(text, encoding="utf-8")
        ground_truth[fname] = truth
        record_id += 1

    # Records with missing critical fields
    for _ in range(n_missing):
        category = random.choice(categories)
        result_raw = random.choice(result_options)
        drop = random.sample(["permit_number", "site_address"], k=random.randint(1, 2))
        text, truth = generate_record(record_id, category, result_raw, drop_fields=drop)
        fname = f"synthetic_{record_id:03d}.txt"
        (OUT_DIR / fname).write_text(text, encoding="utf-8")
        ground_truth[fname] = truth
        record_id += 1

    # Write ground truth
    TRUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRUTH_PATH.write_text(json.dumps(ground_truth, indent=2), encoding="utf-8")

    print(f"Generated {record_id - 1} synthetic test files in {OUT_DIR}")
    print(f"  Clean: {n_clean}  |  Noisy: {n_noisy}  |  Missing fields: {n_missing}")
    print(f"Ground truth written to {TRUTH_PATH}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate synthetic test data for SmartRoute evaluation.")
    parser.add_argument("--count", type=int, default=100, choices=[25, 50, 100],
                        help="Number of records to generate (default: 100)")
    parser.add_argument("--clean", action="store_true",
                        help="Delete all synthetic data and exit")
    args = parser.parse_args()

    if args.clean:
        clean_synthetic_data()
        return

    generate_dataset(args.count)


if __name__ == "__main__":
    main()

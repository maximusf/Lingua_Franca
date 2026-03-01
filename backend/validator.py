"""
SmartRoute Validator — Normalizes raw LLM output into a typed InspectionRecord.

Pipeline:  LLMExtraction → validate() → InspectionRecord (without routing — urgency.py adds that)

Handles:
  - Result normalization  ("approved", "Pass", "fail" → enum)
  - Permit category classification (keyword matching on raw strings)
  - Confidence scoring (how many fields did the LLM actually extract?)
  - Human review flagging (missing critical fields, low confidence)
"""

from __future__ import annotations

from backend.schema import (
    InspectionRecord,
    InspectionResult,
    LLMExtraction,
    PermitCategory,
)


# ─── Result Normalization ────────────────────────────────────────────────────

_RESULT_MAP: dict[str, InspectionResult] = {
    "pass": InspectionResult.PASS_,
    "passed": InspectionResult.PASS_,
    "fail": InspectionResult.FAIL,
    "failed": InspectionResult.FAIL,
    "approved": InspectionResult.APPROVED,
    "rejected": InspectionResult.REJECTED,
    "denied": InspectionResult.REJECTED,
    "pending": InspectionResult.PENDING,
}


def normalize_result(raw: str | None) -> InspectionResult:
    if not raw:
        return InspectionResult.UNKNOWN
    return _RESULT_MAP.get(raw.strip().lower(), InspectionResult.UNKNOWN)


# ─── Permit Category Classification ─────────────────────────────────────────
# Keyword matching against permit_category, inspection_type, and description.
# Order matters — first match wins. More specific patterns come first.

_CATEGORY_RULES: list[tuple[list[str], PermitCategory]] = [
    # Mobile home — check first since "mobile home" is very specific
    (["mobile home", "mobile_home", "mh-", "manufactured", "dw mh"],
     PermitCategory.MOBILE_HOME),

    # Accessory structure
    (["accessory", "detached garage", "shed", "carport"],
     PermitCategory.ACCESSORY_STRUCTURE),

    # Temp power — "temp" before "residential" since "res temp electric" has both
    (["temp power", "temp pole", "temp electric", "temp/perm power",
      "rel temp", "200 amp release"],
     PermitCategory.TEMP_POWER),

    # Commercial
    (["commercial", "comm "],
     PermitCategory.COMMERCIAL),

    # Residential — broadest, checked last
    (["residential", "res gas", "res electric", "res elec",
      "new dwelling", "single family"],
     PermitCategory.RESIDENTIAL),
]


def classify_permit_category(extraction: LLMExtraction) -> PermitCategory:
    """Classify permit category from multiple fields via keyword matching."""
    # Build a search string from all relevant fields
    parts = [
        extraction.permit_category or "",
        extraction.inspection_type or "",
        extraction.description or "",
    ]
    search_text = " ".join(parts).lower()

    for keywords, category in _CATEGORY_RULES:
        for kw in keywords:
            if kw in search_text:
                return category

    return PermitCategory.UNKNOWN


# ─── Confidence Scoring ──────────────────────────────────────────────────────

# Critical fields worth more toward confidence
_CRITICAL_FIELDS = ["permit_number", "inspection_type", "result", "site_address"]
_CRITICAL_WEIGHT = 0.20  # each critical field = 0.20 (4 fields × 0.20 = 0.80 max)

_SECONDARY_FIELDS = [
    "county", "inspection_date", "description",
    "contact_name", "contact_phone", "inspector",
]
_SECONDARY_WEIGHT = 0.033  # 6 fields × 0.033 ≈ 0.20 max


def compute_confidence(extraction: LLMExtraction) -> float:
    score = 0.0
    data = extraction.model_dump()

    for field in _CRITICAL_FIELDS:
        if data.get(field):
            score += _CRITICAL_WEIGHT

    for field in _SECONDARY_FIELDS:
        if data.get(field):
            score += _SECONDARY_WEIGHT

    return round(min(1.0, score), 2)


# ─── Human Review Flagging ───────────────────────────────────────────────────

def check_human_review(
    extraction: LLMExtraction,
    result: InspectionResult,
    confidence: float,
) -> tuple[bool, str | None]:
    """Returns (flag, reason) for whether this record needs human review."""
    reasons: list[str] = []

    if confidence < 0.5:
        reasons.append(f"Low confidence ({confidence})")

    if result == InspectionResult.UNKNOWN:
        reasons.append("Could not determine inspection result")

    if not extraction.site_address:
        reasons.append("Missing site address")

    if not extraction.permit_number:
        reasons.append("Missing permit number")

    if reasons:
        return True, "; ".join(reasons)
    return False, None


# ─── Main Validation Entry Point ─────────────────────────────────────────────

def validate(extraction: LLMExtraction, raw_input: str) -> InspectionRecord:
    """
    Normalize an LLMExtraction into a clean InspectionRecord.
    Does NOT set urgency/routing — that's urgency.py's job.
    """
    result = normalize_result(extraction.result)
    category = classify_permit_category(extraction)
    confidence = compute_confidence(extraction)
    flag, reason = check_human_review(extraction, result, confidence)

    return InspectionRecord(
        raw_input=raw_input,
        permit_number=extraction.permit_number,
        inspection_type=extraction.inspection_type,
        result=result,
        permit_category=category,
        site_address=extraction.site_address,
        county=extraction.county,
        inspection_date=extraction.inspection_date,
        description=extraction.description,
        contact_name=extraction.contact_name,
        contact_phone=extraction.contact_phone,
        contact_email=extraction.contact_email,
        inspector=extraction.inspector,
        confidence_score=confidence,
        human_review_flag=flag,
        review_reason=reason,
    )

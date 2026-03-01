"""
SmartRoute Schema — Canonical data models for inspection record processing.

Every component builds to these models:
  Extractor  → LLMExtraction   (raw LLM output, all fields nullable)
  Validator  → InspectionRecord (normalized, typed, defaults applied)
  Urgency    → enriches InspectionRecord with routing fields
"""

from __future__ import annotations

import uuid # for generating unique incident IDs
from datetime import datetime # for timestamps
from enum import Enum # for defining categorical fields
from typing import Optional # for optional fields

from pydantic import BaseModel, Field


# ─── Enums ───────────────────────────────────────────────────────────────────

# Enums for normalized fields. These help ensure consistent values
#  for key fields like inspection results and permit categories, 
# which may be expressed in many different ways in the raw data.
class InspectionResult(str, Enum):
    """Normalized inspection outcomes. Validator maps raw strings to these."""
    PASS_ = "PASS" # "PASS" is a reserved keyword in Python, so we use "PASS_"
    FAIL = "FAIL"
    # for cases where "approved" and "rejected" are used instead of "pass/fail"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED" 
    # for utility release notifications (no pass/fail, just a release)
    RELEASED = "RELEASED"
    # for inspections that are not yet completed or have ambiguous results
    PENDING = "PENDING"
    # fallback for unrecognized or missing results
    UNKNOWN = "UNKNOWN"

# Permit categories based on observed data. 
# validator.py maps raw strings to these.
class PermitCategory(str, Enum):
    """
    Derived from real permit data seen in Dominion Energy samples:
      - Residential:            RES GAS TEST, RES TEMP ELECTRIC, Residential
      - Commercial:             Commercial inspections
      - Mobile Home:            Mobile Home, MH-PERMANENT SERVICE, Manufactured Home Set Up
      - Temp Power:             Temp Power Pole, OK FOR TEMP/PERM POWER, REL TEMP ELECTRIC
      - Accessory Structure:    Res Accessory Structure, Detached Garage
      - Unknown:                fallback
    """
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    MOBILE_HOME = "mobile_home"
    TEMP_POWER = "temp_power"
    ACCESSORY_STRUCTURE = "accessory_structure"
    UNKNOWN = "unknown"

# Urgency levels for routing. 
# These are determined by the urgency.py module 
# based on the inspection record's content.
class UrgencyLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

# Routing destinations based on project spec.
class RoutingDestination(str, Enum):
    """
    Routing targets from the project spec:
      - safety_team   ← gas/safety hazards
      - field_ops     ← electrical releases, field work needed
      - scheduling    ← routine approvals, passed inspections
      - maintenance   ← infrastructure/maintenance items
      - human_review  ← ambiguous, low confidence, missing data
    """
    FIELD_OPS = "field_ops"
    SCHEDULING = "scheduling"
    SAFETY_TEAM = "safety_team"
    MAINTENANCE = "maintenance"
    HUMAN_REVIEW = "human_review"


# ─── LLM Extraction Model ───────────────────────────────────────────────────
# What we ask the LLM to return. All fields Optional[str] because
# the LLM may not find every field in every document format.
#
# The extraction prompt (prompts/extraction.txt) MUST match these field names.

# This is the raw output from the LLM, before any validation or normalization.
# Ex: the LLM might return "Pass" for the result, 
# which the validator will map to InspectionResult.PASS.
# The validator also handles cases where the LLM returns something unexpected,
# like "Approved" or "Rejected", and maps those to APPROVED/REJECTED enums.
class LLMExtraction(BaseModel):
    """Raw fields extracted by the LLM. No normalization — just strings."""

    permit_number: Optional[str] = None
    inspection_type: Optional[str] = None
    result: Optional[str] = None
    permit_category: Optional[str] = None
    site_address: Optional[str] = None
    county: Optional[str] = None
    inspection_date: Optional[str] = None
    description: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    inspector: Optional[str] = None


# ─── Canonical Output Record ────────────────────────────────────────────────
# The final structured record after validation, normalization, and routing.
# This is what the UI displays and what downstream systems consume.
class InspectionRecord(BaseModel):
    """Complete inspection record — the single source of truth."""

    # --- Auto-generated metadata ---
    incident_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    raw_input: str

    # --- Extracted fields (from LLM, cleaned by validator) ---
    permit_number: Optional[str] = None
    inspection_type: Optional[str] = None
    result: InspectionResult = InspectionResult.UNKNOWN
    permit_category: PermitCategory = PermitCategory.UNKNOWN
    site_address: Optional[str] = None
    county: Optional[str] = None
    inspection_date: Optional[str] = None
    description: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    inspector: Optional[str] = None

    # --- Computed fields (set by urgency.py routing engine) ---
    urgency: UrgencyLevel = UrgencyLevel.MEDIUM
    urgency_score: int = Field(default=3, ge=1, le=5)
    routed_to: RoutingDestination = RoutingDestination.HUMAN_REVIEW
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    human_review_flag: bool = True
    review_reason: Optional[str] = "Pending validation"


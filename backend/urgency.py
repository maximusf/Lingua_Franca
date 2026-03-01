"""
SmartRoute Urgency & Routing — Deterministic rules engine.

Takes a validated InspectionRecord and enriches it with:
  - urgency       (critical / high / medium / low)
  - urgency_score (1–5)
  - routed_to     (safety_team / field_ops / scheduling / maintenance / human_review)

Rules are evaluated top-to-bottom. First match wins.
Designed from the project spec + real Dominion Energy sample data:
  - Gas/safety → safety_team, critical (5)
  - Electrical release → field_ops, high (4)
  - Missing result → human_review, medium (3)
  - Routine pass/approval → scheduling, low (1)
"""

from __future__ import annotations

from backend.schema import (
    InspectionRecord,
    InspectionResult,
    PermitCategory,
    RoutingDestination,
    UrgencyLevel,
)


# ─── Rule Definitions ────────────────────────────────────────────────────────
# Each rule is a function: InspectionRecord → (UrgencyLevel, int, RoutingDestination) | None
# Return None to skip to the next rule. First non-None result wins.

def _rule_human_review_flag(r: InspectionRecord) -> tuple[UrgencyLevel, int, RoutingDestination] | None:
    """Already flagged for human review by validator → route there immediately."""
    if r.human_review_flag and r.confidence_score < 0.3:
        return UrgencyLevel.HIGH, 4, RoutingDestination.HUMAN_REVIEW
    return None


def _rule_gas_safety(r: InspectionRecord) -> tuple[UrgencyLevel, int, RoutingDestination] | None:
    """Gas test or safety-related inspection with FAIL → critical, safety_team."""
    itype = (r.inspection_type or "").lower()
    desc = (r.description or "").lower()
    text = f"{itype} {desc}"

    is_gas_safety = any(kw in text for kw in ["gas", "leak", "safety", "hazard"])

    if is_gas_safety and r.result == InspectionResult.FAIL:
        return UrgencyLevel.CRITICAL, 5, RoutingDestination.SAFETY_TEAM
    if is_gas_safety:
        return UrgencyLevel.HIGH, 4, RoutingDestination.SAFETY_TEAM
    return None


def _rule_electrical_release(r: InspectionRecord) -> tuple[UrgencyLevel, int, RoutingDestination] | None:
    """Electrical release / temp power → field_ops, high."""
    itype = (r.inspection_type or "").lower()
    desc = (r.description or "").lower()
    text = f"{itype} {desc}"

    is_electrical = any(kw in text for kw in [
        "electrical release", "temp electric", "temp power",
        "amp release", "perm power", "rel temp", "elec",
    ])

    if is_electrical:
        if r.result in (InspectionResult.PASS_, InspectionResult.APPROVED, InspectionResult.RELEASED):
            return UrgencyLevel.HIGH, 4, RoutingDestination.FIELD_OPS
        # Electrical but not yet passed — still needs attention
        return UrgencyLevel.HIGH, 4, RoutingDestination.FIELD_OPS
    return None


def _rule_missing_result(r: InspectionRecord) -> tuple[UrgencyLevel, int, RoutingDestination] | None:
    """Result unknown or missing → needs human review."""
    if r.result == InspectionResult.UNKNOWN:
        return UrgencyLevel.MEDIUM, 3, RoutingDestination.HUMAN_REVIEW
    return None


def _rule_fail(r: InspectionRecord) -> tuple[UrgencyLevel, int, RoutingDestination] | None:
    """Non-gas/non-electrical FAIL → medium urgency, human review."""
    if r.result in (InspectionResult.FAIL, InspectionResult.REJECTED):
        return UrgencyLevel.MEDIUM, 3, RoutingDestination.HUMAN_REVIEW
    return None


def _rule_mobile_home(r: InspectionRecord) -> tuple[UrgencyLevel, int, RoutingDestination] | None:
    """Mobile home inspections with pass → scheduling."""
    if r.permit_category == PermitCategory.MOBILE_HOME:
        if r.result in (InspectionResult.PASS_, InspectionResult.APPROVED, InspectionResult.RELEASED):
            return UrgencyLevel.LOW, 2, RoutingDestination.SCHEDULING
        return UrgencyLevel.MEDIUM, 3, RoutingDestination.HUMAN_REVIEW
    return None


def _rule_routine_pass(r: InspectionRecord) -> tuple[UrgencyLevel, int, RoutingDestination] | None:
    """Routine pass or approval → scheduling, low urgency."""
    if r.result in (InspectionResult.PASS_, InspectionResult.APPROVED, InspectionResult.RELEASED):
        return UrgencyLevel.LOW, 1, RoutingDestination.SCHEDULING
    return None


# Rule chain — evaluated in order, first match wins
_RULES = [
    _rule_human_review_flag,
    _rule_gas_safety,
    _rule_electrical_release,
    _rule_missing_result,
    _rule_fail,
    _rule_mobile_home,
    _rule_routine_pass,
]

# Default if no rule matches
_DEFAULT = (UrgencyLevel.MEDIUM, 3, RoutingDestination.HUMAN_REVIEW)


# ─── Public API ──────────────────────────────────────────────────────────────

def apply_routing(record: InspectionRecord) -> InspectionRecord:
    """
    Evaluate rules and return a new InspectionRecord with urgency/routing set.
    Does not mutate the input.
    """
    for rule in _RULES:
        result = rule(record)
        if result is not None:
            urgency, score, destination = result
            return record.model_copy(update={
                "urgency": urgency,
                "urgency_score": score,
                "routed_to": destination,
            })

    urgency, score, destination = _DEFAULT
    return record.model_copy(update={
        "urgency": urgency,
        "urgency_score": score,
        "routed_to": destination,
    })

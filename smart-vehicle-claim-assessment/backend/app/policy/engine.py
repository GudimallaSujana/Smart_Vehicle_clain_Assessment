from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import get_settings


def _load_rules() -> Dict[str, Any]:
    path = get_settings().config_dir / "policy_rules.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "own_damage_policy_types": ["comprehensive", "package", "own damage"],
            "third_party_only_terms": ["third party", "third-party"],
        }


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(str(value).strip(), fmt)
        except Exception:
            continue
    return None


def _norm_reg(value: Optional[str]) -> str:
    return "" if not value else str(value).upper().replace(" ", "").replace("-", "")


def _factor(name: str, evidence: str, effect: str, status: str) -> Dict[str, str]:
    return {"factor": name, "evidence": evidence, "effect": effect, "status": status}


def analyze_policy(claim: Dict[str, Any], damage_assessments: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Configurable policy decision-support analysis.

    Returns ELIGIBLE / NOT_ELIGIBLE / NEEDS_VERIFICATION / SUSPICIOUS_EVIDENCE.
    This never states that a claim will be approved.
    """

    rules = _load_rules()
    vehicle = claim.get("vehicle") or {}
    policy = claim.get("policy") or {}
    docs = claim.get("documents") or []
    factors: List[Dict[str, str]] = []
    outcome = "ELIGIBLE"

    if not policy:
        factors.append(_factor("Policy information", "No structured policy record available", "Manual review required", "NEEDS_VERIFICATION"))
        return {
            "outcome": "NEEDS_VERIFICATION",
            "factors": factors,
            "manual_review_required": True,
            "disclaimer": "Policy conditions are configurable. Upload actual policy wording for insurer-specific analysis.",
        }

    # Merge extracted policy fields from document if available.
    extracted_policy_fields: Dict[str, Any] = {}
    for doc in docs:
        if "policy" in str(doc.get("document_type") or "").lower():
            extracted_policy_fields.update(doc.get("extracted_fields") or {})
    merged_policy = {**policy, **{k: v for k, v in extracted_policy_fields.items() if v not in (None, "", [])}}

    accident = _parse_date(claim.get("accident_date"))
    start = _parse_date(merged_policy.get("start_date"))
    end = _parse_date(merged_policy.get("end_date"))
    if accident and start and end:
        if start <= accident <= end:
            factors.append(_factor("Policy validity", f"Accident date {claim.get('accident_date')} lies within {merged_policy.get('start_date')} to {merged_policy.get('end_date')}", "Supports potential eligibility", "ELIGIBLE"))
        else:
            outcome = "NOT_ELIGIBLE"
            factors.append(_factor("Policy validity", f"Accident date {claim.get('accident_date')} is outside policy period {merged_policy.get('start_date')} to {merged_policy.get('end_date')}", "May make own-damage claim ineligible unless insurer validates another active policy", "NOT_ELIGIBLE"))
    else:
        outcome = _downgrade(outcome, "NEEDS_VERIFICATION")
        factors.append(_factor("Policy validity", "Policy dates or accident date are missing/uncertain", "Requires manual verification/correction", "NEEDS_VERIFICATION"))

    policy_type = str(merged_policy.get("policy_type") or "").lower()
    if any(term in policy_type for term in rules.get("third_party_only_terms", [])):
        outcome = _downgrade(outcome, "NOT_ELIGIBLE")
        factors.append(_factor("Policy type", merged_policy.get("policy_type") or "Third-party only", "Third-party-only policies generally do not cover own vehicle damage; verify policy wording", "NOT_ELIGIBLE"))
    elif any(term in policy_type for term in rules.get("own_damage_policy_types", [])):
        factors.append(_factor("Policy type", merged_policy.get("policy_type") or "Own damage/comprehensive", "Policy type appears to include own-damage decision-support pathway", "ELIGIBLE"))
    else:
        outcome = _downgrade(outcome, "NEEDS_VERIFICATION")
        factors.append(_factor("Policy type", merged_policy.get("policy_type") or "Missing", "Cannot determine whether own damage is covered", "NEEDS_VERIFICATION"))

    claim_reg = _norm_reg(vehicle.get("registration_number"))
    policy_reg = _norm_reg(merged_policy.get("registration_number"))
    if claim_reg and policy_reg:
        if claim_reg == policy_reg:
            factors.append(_factor("Vehicle registration", f"Policy/RC registration {policy_reg} matches claim vehicle", "Supports consistency", "ELIGIBLE"))
        else:
            outcome = "SUSPICIOUS_EVIDENCE"
            factors.append(_factor("Vehicle registration", f"Claim vehicle {claim_reg} differs from policy/document {policy_reg}", "High-priority vehicle identity consistency issue; manual verification required", "SUSPICIOUS_EVIDENCE"))
    else:
        outcome = _downgrade(outcome, "NEEDS_VERIFICATION")
        factors.append(_factor("Vehicle registration", "Registration number missing from claim or policy extraction", "Requires user correction/manual review", "NEEDS_VERIFICATION"))

    deductible = merged_policy.get("deductible")
    if deductible is not None:
        factors.append(_factor("Deductible / Excess", f"₹{float(deductible):,.0f}" if _is_number(deductible) else str(deductible), "Reduces preliminary settlement estimate", "ELIGIBLE"))
    else:
        outcome = _downgrade(outcome, "NEEDS_VERIFICATION")
        factors.append(_factor("Deductible / Excess", "Deductible not found", "Settlement estimate should not be finalized until deductible is known", "NEEDS_VERIFICATION"))

    idv = merged_policy.get("idv")
    if idv is not None:
        factors.append(_factor("IDV", f"₹{float(idv):,.0f}" if _is_number(idv) else str(idv), "Acts as a policy limit/cap where applicable", "ELIGIBLE"))
    else:
        factors.append(_factor("IDV", "IDV not extracted", "May be needed for total-loss/high-value assessment", "NEEDS_VERIFICATION"))
        if damage_assessments and any(str(d.get("severity")) == "Severe" for d in damage_assessments):
            outcome = _downgrade(outcome, "NEEDS_VERIFICATION")

    exclusions = merged_policy.get("exclusions") or []
    desc = str(claim.get("accident_description") or "").lower()
    exclusions_text = " ".join(exclusions).lower() if isinstance(exclusions, list) else str(exclusions).lower()
    if exclusions_text and desc:
        overlapping = [word for word in ["flood", "fire", "commercial", "racing", "drunk", "wear and tear"] if word in desc and word in exclusions_text]
        if overlapping:
            outcome = _downgrade(outcome, "NEEDS_VERIFICATION")
            factors.append(_factor("Exclusions", f"Possible overlap with exclusion terms: {', '.join(overlapping)}", "Requires policy-wording review; no automatic rejection", "NEEDS_VERIFICATION"))
        else:
            factors.append(_factor("Exclusions", "No obvious keyword overlap between accident description and extracted exclusions", "No exclusion signal found by simple parser", "ELIGIBLE"))
    else:
        factors.append(_factor("Exclusions", "Exclusion wording or accident description missing", "Insurer-specific wording should be reviewed", "NEEDS_VERIFICATION"))

    manual = outcome != "ELIGIBLE"
    return {
        "outcome": outcome,
        "factors": factors,
        "manual_review_required": manual,
        "merged_policy": merged_policy,
        "rule_version": rules.get("version", "unknown"),
        "disclaimer": "This configurable engine provides preliminary decision support only. It is not insurer-specific legal advice or claim approval.",
    }


def _is_number(value: Any) -> bool:
    try:
        float(value)
        return True
    except Exception:
        return False


def _downgrade(current: str, candidate: str) -> str:
    order = {"ELIGIBLE": 0, "NEEDS_VERIFICATION": 1, "NOT_ELIGIBLE": 2, "SUSPICIOUS_EVIDENCE": 3}
    return candidate if order.get(candidate, 0) > order.get(current, 0) else current

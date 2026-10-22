from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from app.vision.image_quality import hamming_hash

PRIMARY_OUTCOMES = ["VERIFIED", "ELIGIBLE", "NEEDS_VERIFICATION", "REJECTED", "INELIGIBLE", "SUSPICIOUS_EVIDENCE"]


def _norm_reg(value: Optional[str]) -> str:
    return "" if not value else str(value).upper().replace(" ", "").replace("-", "")


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt)
        except Exception:
            continue
    return None


def _check(check_name: str, status: str, explanation: str, evidence: str = "", can_continue: bool = True, recommended_action: str = "") -> Dict[str, Any]:
    return {
        "check_name": check_name,
        "status": status,
        "explanation": explanation,
        "evidence": evidence,
        "can_continue": can_continue,
        "recommended_action": recommended_action,
    }


def build_evidence_checks(claim: Dict[str, Any], image_results: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    images = claim.get("images") or []
    documents = claim.get("documents") or []
    vehicle = claim.get("vehicle") or {}
    policy = claim.get("policy") or {}
    damage_assessments = claim.get("damage_assessments") or []
    checks: List[Dict[str, Any]] = []

    # Image completeness
    view_types = [str(i.get("view_type") or "").lower() for i in images]
    has_close = any("close" in v or "damage" in v for v in view_types)
    has_context = len(images) >= 2 or any(v in {"front", "rear", "left side", "right side", "side"} for v in view_types)
    if not images:
        checks.append(_check("Evidence completeness", "NEEDS_VERIFICATION", "No accident images have been uploaded.", "0 images", False, "Upload accident photos including full vehicle and damaged close-up."))
    elif len(images) == 1 or not (has_close and has_context):
        checks.append(_check("Evidence completeness", "NEEDS_VERIFICATION", "Insufficient visual evidence for reliable assessment.", f"Uploaded views: {', '.join(view_types) or 'unspecified'}", True, "Upload front/rear/side context and a close-up of the damaged area."))
    else:
        checks.append(_check("Evidence completeness", "VERIFIED", "Uploaded images include multiple views and/or damaged area close-up.", f"{len(images)} images: {', '.join(view_types)}", True, "Continue."))

    # Image quality
    fail = [i for i in images if (i.get("quality_json") or {}).get("status") == "FAIL"]
    warn = [i for i in images if (i.get("quality_json") or {}).get("status") == "WARN"]
    if fail:
        checks.append(_check("Image quality", "NEEDS_VERIFICATION", "One or more images are too blurry/corrupted/low quality for reliable assessment.", f"Failed images: {len(fail)}", False, "Re-upload clearer images."))
    elif warn:
        checks.append(_check("Image quality", "NEEDS_VERIFICATION", "Some images have quality warnings such as blur, low light, or low resolution.", f"Warnings in {len(warn)} image(s)", True, "Manual review or clearer replacement images recommended."))
    elif images:
        checks.append(_check("Image quality", "VERIFIED", "Images passed baseline quality checks.", f"{len(images)} image(s) checked", True, "Continue."))

    # Duplication
    exact_pairs = []
    near_pairs = []
    for idx, a in enumerate(images):
        for b in images[idx + 1 :]:
            if a.get("sha256") and a.get("sha256") == b.get("sha256"):
                exact_pairs.append((a.get("image_id"), b.get("image_id")))
            elif a.get("perceptual_hash") and b.get("perceptual_hash") and hamming_hash(a["perceptual_hash"], b["perceptual_hash"]) <= 5:
                near_pairs.append((a.get("image_id"), b.get("image_id")))
    if exact_pairs or near_pairs:
        checks.append(_check("Duplicate image reuse", "NEEDS_VERIFICATION", "Duplicate or near-duplicate uploads were detected. They are not rejected but are not double-counted.", f"Exact: {len(exact_pairs)}, near: {len(near_pairs)}", True, "Confirm duplicate uploads or provide additional unique angles."))
    elif images:
        checks.append(_check("Duplicate image reuse", "VERIFIED", "No duplicate images were detected within this claim.", "Perceptual and SHA-256 checks completed", True, "Continue."))

    # Document availability
    doc_types = {str(d.get("document_type") or "").lower() for d in documents}
    missing_docs = [name for name in ["rc", "policy"] if not any(name in t for t in doc_types)]
    if missing_docs:
        checks.append(_check("Required document availability", "NEEDS_VERIFICATION", "Important documents are missing. A missing document should route to verification, not automatic rejection.", f"Missing: {', '.join(missing_docs)}", True, "Upload RC and insurance policy documents where available."))
    else:
        checks.append(_check("Required document availability", "VERIFIED", "RC and policy documents are present.", f"Documents: {', '.join(sorted(doc_types))}", True, "Continue."))

    # Cross-document registration consistency
    claim_reg = _norm_reg(vehicle.get("registration_number"))
    extracted_regs = []
    for doc in documents:
        fields = doc.get("extracted_fields") or {}
        reg = _norm_reg(fields.get("registration_number") or fields.get("vehicle_registration_number"))
        if reg:
            extracted_regs.append((doc.get("document_type"), reg))
    mismatches = [(typ, reg) for typ, reg in extracted_regs if claim_reg and reg and reg != claim_reg]
    if mismatches:
        checks.append(_check("Vehicle identity / registration consistency", "SUSPICIOUS_EVIDENCE", "Registration number in uploaded documents does not match the claim vehicle number. This requires manual verification.", f"Claim: {claim_reg}; document values: {extracted_regs}", True, "Verify RC/policy and vehicle identity before relying on assessment."))
    elif claim_reg and extracted_regs:
        checks.append(_check("Vehicle identity / registration consistency", "VERIFIED", "Document registration number matches the claim vehicle number.", f"Registration: {claim_reg}", True, "Continue."))
    else:
        checks.append(_check("Vehicle identity / registration consistency", "NEEDS_VERIFICATION", "Number-plate/registration consistency could not be independently verified from available evidence.", "No reliable extracted registration in documents or images", True, "Upload clear RC/policy and a visible number-plate image where appropriate."))

    # Policy dates/timeline
    accident_date = _parse_date(claim.get("accident_date"))
    start = _parse_date(policy.get("start_date") if policy else None)
    end = _parse_date(policy.get("end_date") if policy else None)
    if policy and accident_date and start and end:
        if start <= accident_date <= end:
            checks.append(_check("Policy validity on accident date", "ELIGIBLE", "Policy dates indicate the policy was active on the reported accident date.", f"Accident {claim.get('accident_date')} between {policy.get('start_date')} and {policy.get('end_date')}", True, "Continue."))
        else:
            checks.append(_check("Policy validity on accident date", "INELIGIBLE", "Reported accident date falls outside the configured policy period.", f"Accident {claim.get('accident_date')}; policy {policy.get('start_date')} to {policy.get('end_date')}", True, "Manual verification with insurer required."))
    else:
        checks.append(_check("Policy validity on accident date", "NEEDS_VERIFICATION", "Policy validity could not be determined because policy dates or accident date are missing/uncertain.", "Missing date fields", True, "Correct extracted policy dates before assessment."))

    # OCR confidence/document processing
    low_ocr = [d for d in documents if d.get("ocr_confidence") is not None and d.get("ocr_confidence") < 0.55]
    no_text = [d for d in documents if not d.get("extracted_text")]
    if low_ocr or no_text:
        checks.append(_check("OCR/document readability", "NEEDS_VERIFICATION", "Some documents could not be read reliably by OCR. Low confidence values should be corrected before assessment.", f"Low OCR: {len(low_ocr)}, no text: {len(no_text)}", True, "Review/correct extracted fields or upload clearer documents."))
    elif documents:
        checks.append(_check("OCR/document readability", "VERIFIED", "Uploaded document text was extracted or parsed with usable confidence.", f"{len(documents)} documents", True, "Continue."))

    # Authenticity / AI-edited caveat. No authoritative detector bundled.
    checks.append(_check("Image/document authenticity", "NEEDS_VERIFICATION", "No authoritative AI-generation or manipulation detector is bundled. Missing metadata alone is not treated as fraud. Suspicious visual/document artifacts should be reviewed by a human.", "Heuristic authenticity checks only", True, "Manual review if artifacts, altered plates, inconsistent shadows, or suspicious document formatting are observed."))

    # Accident description consistency
    desc = str(claim.get("accident_description") or "").lower()
    parts = " ".join(str(d.get("damaged_part") or "").lower() for d in damage_assessments)
    if desc and parts:
        inconsistent = False
        if "rear" in desc and "front" in parts and "rear" not in parts:
            inconsistent = True
        if "front" in desc and "rear" in parts and "front" not in parts:
            inconsistent = True
        if inconsistent:
            checks.append(_check("Accident-to-damage consistency", "NEEDS_VERIFICATION", "Reported accident description does not appear consistent with detected damage.", f"Description: {desc[:120]}; detected parts: {parts}", True, "Human reviewer should compare accident narrative with all photos."))
        else:
            checks.append(_check("Accident-to-damage consistency", "VERIFIED", "No obvious contradiction was found between reported description and detected damage labels.", f"Detected parts: {parts}", True, "Continue."))
    else:
        checks.append(_check("Accident-to-damage consistency", "NEEDS_VERIFICATION", "Not enough accident narrative or damage evidence to check consistency.", "Missing description or damage findings", True, "Provide accident details and clearer photos."))

    # Manual review routing summary
    high_risk_status = any(c["status"] in {"SUSPICIOUS_EVIDENCE", "INELIGIBLE", "REJECTED"} for c in checks)
    needs = any(c["status"] == "NEEDS_VERIFICATION" for c in checks)
    if high_risk_status:
        overall = "SUSPICIOUS_EVIDENCE"
    elif needs:
        overall = "NEEDS_VERIFICATION"
    else:
        overall = "VERIFIED"
    return {
        "overall_status": overall,
        "manual_review_required": overall != "VERIFIED",
        "checks": checks,
        "note": "Validation checks are decision-support signals. They do not accuse fraud and do not make legally binding claim decisions.",
    }

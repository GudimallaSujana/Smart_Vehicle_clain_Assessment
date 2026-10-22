from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

REGISTRATION_RE = re.compile(r"\b([A-Z]{2}\s?\d{1,2}\s?[A-Z]{1,3}\s?\d{4})\b", re.IGNORECASE)
POLICY_RE = re.compile(r"(?:policy\s*(?:no\.?|number)\s*[:\-]?\s*)([A-Z0-9\-/]{5,})", re.IGNORECASE)
CLAIM_REF_RE = re.compile(r"(?:claim\s*(?:ref(?:erence)?|no\.?|number)\s*[:\-]?\s*)([A-Z0-9\-/]{5,})", re.IGNORECASE)
DL_RE = re.compile(r"(?:DL\s*(?:No\.?|Number)?\s*[:\-]?\s*|Licence\s*(?:No\.?|Number)\s*[:\-]?\s*)([A-Z0-9\-/]{6,})", re.IGNORECASE)
DATE_RE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b")
AMOUNT_RE = re.compile(r"(?:₹|Rs\.?|INR)?\s*([0-9]{1,3}(?:[, ]?[0-9]{2,3})+(?:\.\d+)?|[0-9]+(?:\.\d+)?)")


def clean_text(text: str) -> str:
    text = text or ""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_registration(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def parse_amount(value: str) -> Optional[float]:
    if not value:
        return None
    try:
        return float(value.replace(",", "").replace(" ", ""))
    except Exception:
        return None


def find_amount_near(text: str, labels: List[str]) -> Optional[float]:
    for label in labels:
        # Search within the same line/short neighbourhood and use non-greedy
        # matching so we capture the first amount after the label, not the last
        # digit on the line.
        pattern = re.compile(label + r"[^\n\r]{0,80}?" + AMOUNT_RE.pattern, re.IGNORECASE)
        match = pattern.search(text)
        if match:
            # Last group in nested pattern is the amount.
            amount = match.groups()[-1]
            parsed = parse_amount(amount)
            if parsed is not None:
                return parsed
    return None


def _first_date_after(text: str, labels: List[str]) -> Optional[str]:
    for label in labels:
        pattern = re.compile(label + r"[^\n\r]{0,80}?" + DATE_RE.pattern, re.IGNORECASE)
        match = pattern.search(text)
        if match:
            return normalize_date(match.groups()[-1])
    return None


def normalize_date(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip().replace(".", "/")
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except Exception:
            continue
    return value


def _field_after_label(text: str, labels: List[str], max_chars: int = 50) -> Optional[str]:
    for label in labels:
        pattern = re.compile(label + r"\s*[:\-]?\s*([^\n\r]{2," + str(max_chars) + r"})", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            return match.group(1).strip(" .:-")
    return None


def extract_fields(text: str, document_type: str = "unknown") -> Dict[str, Any]:
    text = clean_text(text)
    lower = text.lower()
    fields: Dict[str, Any] = {}

    reg = REGISTRATION_RE.search(text)
    if reg:
        fields["registration_number"] = normalize_registration(reg.group(1))

    policy = POLICY_RE.search(text)
    if policy:
        fields["policy_number"] = policy.group(1).strip()
    claim_ref = CLAIM_REF_RE.search(text)
    if claim_ref:
        fields["claim_reference_number"] = claim_ref.group(1).strip()
    dl = DL_RE.search(text)
    if dl:
        fields["driving_licence_number"] = dl.group(1).strip()

    make = _field_after_label(text, [r"Make", r"Vehicle Make", r"Manufacturer"])
    model = _field_after_label(text, [r"Model", r"Vehicle Model"])
    year = _field_after_label(text, [r"Year", r"Mfg\.? Year", r"Manufacturing Year"], 12)
    colour = _field_after_label(text, [r"Colour", r"Color"])
    owner = _field_after_label(text, [r"Owner Name", r"Insured Name", r"Policyholder", r"Name"])
    if make:
        fields["make"] = make.split()[0]
    if model:
        fields["model"] = model
    if year:
        y = re.search(r"\b(19\d{2}|20\d{2})\b", year)
        if y:
            fields["year"] = int(y.group(1))
    if colour:
        fields["colour"] = colour.split()[0]
    if owner:
        fields["owner_or_policyholder_name"] = owner

    if "comprehensive" in lower or "package" in lower:
        fields["policy_type"] = "Comprehensive / Package Policy"
    elif "own damage" in lower or re.search(r"\bod\b", lower):
        fields["policy_type"] = "Own Damage"
    elif "third party" in lower or "third-party" in lower or re.search(r"\btp\b", lower):
        fields["policy_type"] = "Third-Party"

    start_date = _first_date_after(text, [r"Policy Start", r"Start Date", r"From", r"Period of Insurance From"])
    end_date = _first_date_after(text, [r"Policy End", r"End Date", r"To", r"Expiry", r"Valid Upto", r"Valid Until"])
    accident_date = _first_date_after(text, [r"Accident Date", r"Date of Accident"])
    claim_date = _first_date_after(text, [r"Claim Date", r"Date of Claim"])
    licence_expiry = _first_date_after(text, [r"Licence Expiry", r"DL Expiry", r"Valid Till", r"Valid Upto"])
    if start_date:
        fields["start_date"] = start_date
    if end_date:
        fields["end_date"] = end_date
    if accident_date:
        fields["accident_date"] = accident_date
    if claim_date:
        fields["claim_date"] = claim_date
    if licence_expiry:
        fields["licence_expiry_date"] = licence_expiry

    idv = find_amount_near(text, [r"IDV", r"Insured Declared Value"])
    deductible = find_amount_near(text, [r"Deductible", r"Excess", r"Compulsory Deductible"])
    estimate_total = find_amount_near(text, [r"Total", r"Grand Total", r"Repair Estimate", r"Estimated Repair"])
    if idv is not None:
        fields["idv"] = idv
    if deductible is not None:
        fields["deductible"] = deductible
    if estimate_total is not None and document_type.lower() in {"repair_estimate", "repair estimate", "invoice"}:
        fields["repair_estimate_total"] = estimate_total

    coverage = []
    exclusions = []
    for line in text.splitlines():
        l = line.strip()
        if re.search(r"cover(?:age|ed)?", l, re.IGNORECASE) and len(l) < 220:
            coverage.append(l)
        if re.search(r"exclusion|not covered|excluded", l, re.IGNORECASE) and len(l) < 220:
            exclusions.append(l)
    if coverage:
        fields["coverage"] = coverage[:10]
    if exclusions:
        fields["exclusions"] = exclusions[:10]

    # Confidence is extraction confidence, not OCR confidence. Penalize sparse parses.
    expected = {
        "policy": ["policy_number", "policy_type", "start_date", "end_date", "registration_number"],
        "rc": ["registration_number", "make", "model"],
        "licence": ["driving_licence_number", "licence_expiry_date"],
        "repair_estimate": ["repair_estimate_total"],
    }
    key = document_type.lower().replace(" ", "_")
    target = expected.get(key, ["registration_number"])
    present = sum(1 for t in target if fields.get(t))
    fields["field_extraction_confidence"] = round(present / max(len(target), 1), 2)
    fields["raw_text_available"] = bool(text)
    return fields

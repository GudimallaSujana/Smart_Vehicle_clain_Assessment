from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from app import db
from app.config import get_settings
from app.documents.ocr import process_document
from app.estimation.estimator import estimate_cost
from app.policy.engine import analyze_policy
from app.reports.pdf_report import generate_claim_report
from app.schemas import ClaimCreate
from app.utils.security import UploadValidationError, save_upload
from app.vision.damage_analyzer import aggregate_assessments, analyze_single_image
from app.vision.evidence import build_evidence_checks
from app.vision.image_quality import inspect_image_quality

logger = logging.getLogger(__name__)


def create_claim(payload: ClaimCreate) -> Dict[str, Any]:
    db.init_db()
    claim_id = db.create_claim(
        user=payload.user.model_dump(),
        vehicle=payload.vehicle.model_dump(),
        accident=payload.accident.model_dump(),
        policy=payload.policy.model_dump() if payload.policy else None,
        demo_mode=payload.demo_mode,
        manual_repair_estimate=payload.manual_repair_estimate,
    )
    logger.info("claim_created", extra={"claim_id": claim_id})
    claim = db.get_claim(claim_id)
    if not claim:
        raise RuntimeError("Claim creation failed")
    return claim


def save_claim_image(claim_id: str, fileobj, filename: str, view_type: str) -> Dict[str, Any]:
    claim = db.get_claim(claim_id)
    if not claim:
        raise KeyError("Claim not found")
    target, mime, _ = save_upload(fileobj, filename, claim_id, "image")
    quality = inspect_image_quality(target)
    validation_status = "ACCEPTED" if quality.get("can_continue") else "REUPLOAD_REQUIRED"
    image_id = db.insert_image(
        claim_id=claim_id,
        view_type=view_type,
        original_filename=filename,
        stored_path=str(target),
        mime_type=mime,
        sha256=quality.get("sha256", ""),
        perceptual_hash=quality.get("perceptual_hash", ""),
        quality=quality,
        validation_status=validation_status,
    )
    db.update_claim_status(claim_id, "IMAGE_VALIDATION")
    logger.info("image_uploaded", extra={"claim_id": claim_id})
    return db.fetch_one("SELECT * FROM claim_images WHERE image_id=?", (image_id,)) or {}


def save_claim_document(claim_id: str, fileobj, filename: str, document_type: str) -> Dict[str, Any]:
    claim = db.get_claim(claim_id)
    if not claim:
        raise KeyError("Claim not found")
    target, mime, _ = save_upload(fileobj, filename, claim_id, "document")
    ocr = process_document(target, document_type)
    document_id = db.insert_document(
        claim_id=claim_id,
        document_type=document_type,
        original_filename=filename,
        stored_path=str(target),
        mime_type=mime,
        extracted_text=ocr["extracted_text"],
        extracted_fields=ocr["extracted_fields"],
        verification_status=ocr["verification_status"],
        ocr_confidence=ocr.get("ocr_confidence"),
        warnings=ocr.get("warnings") or [],
    )
    _apply_document_fields_to_claim(claim_id, document_type, ocr["extracted_fields"])
    db.update_claim_status(claim_id, "DOCUMENTS_REQUIRED" if ocr["verification_status"] == "NEEDS_USER_REVIEW" else "IMAGE_VALIDATION")
    logger.info("document_uploaded", extra={"claim_id": claim_id})
    return db.fetch_one("SELECT * FROM documents WHERE document_id=?", (document_id,)) or {}


def _apply_document_fields_to_claim(claim_id: str, document_type: str, fields: Dict[str, Any]) -> None:
    # Preserve user-entered values; fill missing policy values from extracted docs.
    claim = db.get_claim(claim_id)
    if not claim:
        return
    if "policy" in document_type.lower():
        policy = claim.get("policy") or {}
        updates = {k: fields.get(k) for k in ["policy_number", "policy_type", "start_date", "end_date", "idv", "deductible", "coverage", "exclusions"] if fields.get(k) is not None and not policy.get(k)}
        if fields.get("registration_number") and not policy.get("registration_number"):
            updates["registration_number"] = fields["registration_number"]
        if updates:
            if policy.get("policy_id"):
                db.execute(
                    """
                    UPDATE policies SET policy_number=COALESCE(?, policy_number), policy_type=COALESCE(?, policy_type),
                        start_date=COALESCE(?, start_date), end_date=COALESCE(?, end_date), idv=COALESCE(?, idv),
                        deductible=COALESCE(?, deductible), coverage=COALESCE(?, coverage), exclusions=COALESCE(?, exclusions), updated_at=?
                    WHERE policy_id=?
                    """,
                    (
                        updates.get("policy_number"),
                        updates.get("policy_type"),
                        updates.get("start_date"),
                        updates.get("end_date"),
                        updates.get("idv"),
                        updates.get("deductible"),
                        db.dumps(updates.get("coverage")) if updates.get("coverage") else None,
                        db.dumps(updates.get("exclusions")) if updates.get("exclusions") else None,
                        db.now_iso(),
                        policy["policy_id"],
                    ),
                )
            else:
                policy_id = db.create_policy(claim["vehicle_id"], updates)
                db.execute("UPDATE claims SET policy_id=?, updated_at=? WHERE claim_id=?", (policy_id, db.now_iso(), claim_id))
    if "rc" in document_type.lower():
        vehicle = claim.get("vehicle") or {}
        db.execute(
            """
            UPDATE vehicles SET registration_number=COALESCE(NULLIF(?, ''), registration_number), make=COALESCE(?, make),
                model=COALESCE(?, model), year=COALESCE(?, year), colour=COALESCE(?, colour)
            WHERE vehicle_id=?
            """,
            (
                fields.get("registration_number") if not vehicle.get("registration_number") else "",
                fields.get("make") if not vehicle.get("make") else None,
                fields.get("model") if not vehicle.get("model") else None,
                fields.get("year") if not vehicle.get("year") else None,
                fields.get("colour") if not vehicle.get("colour") else None,
                vehicle.get("vehicle_id"),
            ),
        )
    if document_type.lower() in {"repair_estimate", "repair estimate", "invoice"} and fields.get("repair_estimate_total"):
        db.execute("UPDATE claims SET manual_repair_estimate=COALESCE(manual_repair_estimate, ?), updated_at=? WHERE claim_id=?", (fields["repair_estimate_total"], db.now_iso(), claim_id))


def analyze_claim(claim_id: str) -> Dict[str, Any]:
    claim = db.get_claim(claim_id)
    if not claim:
        raise KeyError("Claim not found")
    db.update_claim_status(claim_id, "DAMAGE_ASSESSMENT")
    image_results: List[Dict[str, Any]] = []
    for image in claim.get("images") or []:
        if not (image.get("quality_json") or {}).get("can_continue", True):
            analysis = {"image_id": image.get("image_id"), "detections": [], "warnings": ["Image quality failed; damage analysis skipped."], "overlay_path": image.get("stored_path")}
        else:
            analysis = analyze_single_image(image)
        db.update_image_analysis(image["image_id"], analysis, overlay_path=analysis.get("overlay_path"), validation_status="ANALYZED")
        image_results.append(analysis)
    aggregate = aggregate_assessments(image_results)
    db.replace_damage_assessments(claim_id, aggregate["assessments"])

    claim = db.get_claim(claim_id) or claim
    evidence = build_evidence_checks(claim, image_results=image_results)
    db.replace_verification_checks(claim_id, evidence["checks"])

    claim = db.get_claim(claim_id) or claim
    policy_result = analyze_policy(claim, claim.get("damage_assessments") or [])

    claim_for_estimate = db.get_claim(claim_id) or claim
    claim_for_estimate["policy_json"] = policy_result
    estimate = estimate_cost(claim_for_estimate, claim_for_estimate.get("damage_assessments") or [], policy_result)
    db.insert_estimation(claim_id, estimate)

    final_eligibility = _combine_outcomes(evidence.get("overall_status"), policy_result.get("outcome"), estimate.get("status"))
    final_status = "HUMAN_REVIEW" if final_eligibility in {"NEEDS_VERIFICATION", "SUSPICIOUS_EVIDENCE"} else "ESTIMATION"
    if final_eligibility == "NOT_ELIGIBLE":
        final_status = "NEEDS_REVIEW"
    db.update_claim_status(
        claim_id,
        final_status,
        eligibility=final_eligibility,
        estimated_amount=estimate.get("estimated_settlement"),
        validation=evidence,
        policy_analysis=policy_result,
        claim_json={"damage_aggregation": aggregate, "image_results": image_results, "estimate_warnings": estimate.get("warnings")},
    )
    full = db.get_claim(claim_id) or {}
    # Generate report as the final stage. If PDF generation fails, record warning but do not crash analysis.
    try:
        report_path = generate_claim_report(full)
        full["report_path"] = str(report_path)
    except Exception as exc:
        full.setdefault("warnings", []).append(f"PDF generation failed: {type(exc).__name__}")
    logger.info("claim_analyzed", extra={"claim_id": claim_id})
    return full


def _combine_outcomes(evidence_status: str, policy_outcome: str, estimate_status: str) -> str:
    if evidence_status == "SUSPICIOUS_EVIDENCE" or policy_outcome == "SUSPICIOUS_EVIDENCE":
        return "SUSPICIOUS_EVIDENCE"
    if policy_outcome == "NOT_ELIGIBLE":
        return "NOT_ELIGIBLE"
    if evidence_status != "VERIFIED" or policy_outcome != "ELIGIBLE" or estimate_status not in {"PRELIMINARY_ESTIMATE", "NEEDS_DEDUCTIBLE"}:
        return "NEEDS_VERIFICATION"
    return "ELIGIBLE"


def generate_report_for_claim(claim_id: str) -> Path:
    claim = db.get_claim(claim_id)
    if not claim:
        raise KeyError("Claim not found")
    return generate_claim_report(claim)


def seed_demo_claim() -> Dict[str, Any]:
    settings = get_settings()
    from app.demo_data import ensure_demo_assets

    assets = ensure_demo_assets()
    payload = ClaimCreate(
        demo_mode=True,
        user={"name": "Demo Vehicle Owner", "email": "demo@example.com", "contact": "9999999999"},
        vehicle={"registration_number": "TS09AB1234", "make": "DemoMake", "model": "DemoModel", "year": 2021, "vehicle_value": 500000, "colour": "Blue"},
        accident={"accident_date": "2026-09-20", "claim_date": "2026-09-22", "accident_location": "Hyderabad, Telangana", "accident_description": "Front-left impact with bumper scratch and dent after low-speed collision."},
        policy={"policy_number": "DEMO-POL-2026", "policy_type": "Comprehensive / Package Policy", "start_date": "2026-01-01", "end_date": "2026-12-31", "idv": 500000, "deductible": 1000, "coverage": ["Own Damage", "Accidental external damage"], "exclusions": ["Wear and tear", "Mechanical breakdown not arising from accident"]},
        manual_repair_estimate=None,
    )
    claim = create_claim(payload)
    # Copy sample images and documents through the same DB insertion path but without UploadFile streams.
    for sample in assets["images"]:
        quality = inspect_image_quality(sample["path"])
        image_id = db.insert_image(claim["claim_id"], sample["view_type"], Path(sample["path"]).name, str(sample["path"]), "image/png", quality.get("sha256", ""), quality.get("perceptual_hash", ""), quality, "ACCEPTED")
    for doc in assets["documents"]:
        ocr = process_document(doc["path"], doc["document_type"])
        db.insert_document(claim["claim_id"], doc["document_type"], Path(doc["path"]).name, str(doc["path"]), "application/pdf", ocr["extracted_text"], ocr["extracted_fields"], ocr["verification_status"], ocr.get("ocr_confidence"), ocr.get("warnings") or [])
    return analyze_claim(claim["claim_id"])

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import db
from app.config import get_settings
from app.demo_data import ensure_demo_assets
from app.documents.ocr import ocr_availability
from app.estimation.estimator import estimate_cost, load_pricing
from app.policy.engine import analyze_policy
from app.schemas import ClaimCreate, ClaimUpdate, OCRCorrection, PricingItemIn, ReviewDecision, DISCLAIMER
from app.services.claim_service import analyze_claim, create_claim, generate_report_for_claim, save_claim_document, save_claim_image, seed_demo_claim
from app.utils.logging_config import configure_logging
from app.utils.security import UploadValidationError
from app.vision.damage_analyzer import get_device_info, model_status

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    ensure_demo_assets()
    logger.info("backend_started", extra={"claim_id": "-"})
    yield


app = FastAPI(
    title="AI-Based Smart Vehicle Claim Assessment API",
    version="0.1.0",
    description="Indian-focused AI-assisted preliminary vehicle insurance claim assessment backend.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated overlays/reports for local development. Production should use signed URLs/object storage.
app.mount("/outputs", StaticFiles(directory=str(settings.storage_dir)), name="outputs")


@app.exception_handler(UploadValidationError)
def upload_error_handler(_, exc: UploadValidationError):
    return JSONResponse(status_code=400, content={"status": "error", "message": str(exc), "disclaimer": DISCLAIMER})


@app.exception_handler(KeyError)
def not_found_handler(_, exc: KeyError):
    return JSONResponse(status_code=404, content={"status": "error", "message": str(exc), "disclaimer": DISCLAIMER})


@app.get("/api/health")
def health() -> dict:
    device = get_device_info()
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "database": "available" if settings.database_path.parent.exists() else "missing",
        "ml_model": model_status(),
        "ocr": ocr_availability(),
        "device": device,
        "disclaimer": DISCLAIMER,
    }


@app.post("/api/claims")
def post_claim(payload: ClaimCreate) -> dict:
    claim = create_claim(payload)
    return {"status": "success", "message": "Claim created", "claim": claim, "disclaimer": DISCLAIMER}


@app.get("/api/claims")
def get_claims() -> dict:
    return {"status": "success", "claims": db.list_claims(), "disclaimer": DISCLAIMER}


@app.get("/api/claims/{claim_id}")
def get_claim(claim_id: str) -> dict:
    claim = db.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return {"status": "success", "claim": claim, "disclaimer": DISCLAIMER}


@app.patch("/api/claims/{claim_id}")
def patch_claim(claim_id: str, payload: ClaimUpdate) -> dict:
    claim = db.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if payload.manual_repair_estimate is not None:
        db.execute("UPDATE claims SET manual_repair_estimate=?, updated_at=? WHERE claim_id=?", (payload.manual_repair_estimate, db.now_iso(), claim_id))
    # Minimal update path; user corrections to docs have a dedicated endpoint.
    return {"status": "success", "claim": db.get_claim(claim_id), "disclaimer": DISCLAIMER}


@app.post("/api/claims/{claim_id}/images")
def upload_image(claim_id: str, file: UploadFile = File(...), view_type: str = Form("additional_evidence")) -> dict:
    image = save_claim_image(claim_id, file.file, file.filename or "image.jpg", view_type)
    return {"status": "success", "message": "Image uploaded and quality checked", "image": image, "disclaimer": DISCLAIMER}


@app.post("/api/claims/{claim_id}/documents")
def upload_document(claim_id: str, file: UploadFile = File(...), document_type: str = Form("policy")) -> dict:
    document = save_claim_document(claim_id, file.file, file.filename or "document.pdf", document_type)
    return {"status": "success", "message": "Document uploaded and OCR/extraction attempted", "document": document, "disclaimer": DISCLAIMER}


@app.patch("/api/claims/{claim_id}/documents/{document_id}/fields")
def correct_document_fields(claim_id: str, document_id: str, payload: OCRCorrection) -> dict:
    if not db.get_claim(claim_id):
        raise HTTPException(status_code=404, detail="Claim not found")
    doc = db.fetch_one("SELECT * FROM documents WHERE document_id=? AND claim_id=?", (document_id, claim_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.update_document_fields(document_id, payload.fields, payload.verification_status)
    return {"status": "success", "message": "OCR fields corrected", "document": db.fetch_one("SELECT * FROM documents WHERE document_id=?", (document_id,)), "disclaimer": DISCLAIMER}


@app.post("/api/claims/{claim_id}/analyze")
def analyze(claim_id: str) -> dict:
    result = analyze_claim(claim_id)
    return {"status": "success", "message": "Claim analyzed", "claim": result, "disclaimer": DISCLAIMER}


@app.get("/api/claims/{claim_id}/damage")
def get_damage(claim_id: str) -> dict:
    if not db.get_claim(claim_id):
        raise HTTPException(status_code=404, detail="Claim not found")
    return {"status": "success", "damage": db.fetch_all("SELECT * FROM damage_assessments WHERE claim_id=?", (claim_id,)), "disclaimer": DISCLAIMER}


@app.get("/api/claims/{claim_id}/policy")
def get_policy(claim_id: str) -> dict:
    claim = db.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    policy_result = claim.get("policy_json") or analyze_policy(claim, claim.get("damage_assessments") or [])
    return {"status": "success", "policy": policy_result, "disclaimer": DISCLAIMER}


@app.get("/api/claims/{claim_id}/estimate")
def get_estimate(claim_id: str) -> dict:
    claim = db.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    estimate = claim.get("estimation") or estimate_cost(claim, claim.get("damage_assessments") or [], claim.get("policy_json"))
    return {"status": "success", "estimate": estimate, "disclaimer": DISCLAIMER}


@app.get("/api/claims/{claim_id}/verification")
def get_verification(claim_id: str) -> dict:
    claim = db.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return {"status": "success", "verification": claim.get("verification_checks") or [], "overall": claim.get("validation_json"), "disclaimer": DISCLAIMER}


@app.get("/api/claims/{claim_id}/report")
def get_report(claim_id: str):
    path = generate_report_for_claim(claim_id)
    return FileResponse(str(path), filename=path.name, media_type="application/pdf")


@app.get("/api/claims/{claim_id}/images/{image_id}/file")
def get_image_file(claim_id: str, image_id: str, overlay: bool = False):
    image = db.fetch_one("SELECT * FROM claim_images WHERE claim_id=? AND image_id=?", (claim_id, image_id))
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    path = Path(image.get("overlay_path") if overlay and image.get("overlay_path") else image.get("stored_path"))
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")
    return FileResponse(str(path), media_type=image.get("mime_type") or "image/jpeg")


@app.post("/api/demo/seed")
def post_demo_seed() -> dict:
    claim = seed_demo_claim()
    return {"status": "success", "message": "Demo claim created. Demo Data — Not a Real Insurance Claim", "claim": claim, "disclaimer": DISCLAIMER}


@app.get("/api/research/metrics")
def research_metrics() -> dict:
    return {
        "status": "success",
        "metrics": {
            "damage_detection": {"precision": "Not evaluated yet", "recall": "Not evaluated yet", "f1": "Not evaluated yet", "mAP50": "Not evaluated yet", "mAP50_95": "Not evaluated yet"},
            "damage_classification": {"accuracy": "Not evaluated yet", "precision": "Not evaluated yet", "recall": "Not evaluated yet", "f1": "Not evaluated yet"},
            "severity": {"accuracy": "Not evaluated yet", "f1": "Not evaluated yet", "confusion_matrix": []},
            "cost_estimation": {"MAE": "Not evaluated yet", "RMSE": "Not evaluated yet", "MAPE": "Not evaluated yet"},
            "processing": {"average_inference_time_ms": "Not evaluated yet", "ocr_time_ms": "Not evaluated yet", "total_claim_time_ms": "Not evaluated yet"},
        },
        "note": "No experiment results are fabricated. Run scripts/evaluate_model.py after preparing labelled datasets.",
        "disclaimer": DISCLAIMER,
    }


@app.get("/api/admin/pricing")
def get_pricing(demo_only: bool = False) -> dict:
    csv_rows = load_pricing(demo_mode=demo_only)
    db_rows = db.list_pricing_items(demo_only=demo_only)
    return {"status": "success", "pricing": csv_rows + db_rows, "disclaimer": "Configured prices only. Do not use demo prices for real claims."}


@app.post("/api/admin/pricing")
def post_pricing(item: PricingItemIn) -> dict:
    pricing_id = db.insert_pricing_item(item.model_dump())
    return {"status": "success", "pricing_id": pricing_id, "message": "Pricing item stored", "disclaimer": "Only admin-approved pricing should be used for non-demo claims."}


@app.post("/api/claims/{claim_id}/review")
def reviewer_decision(claim_id: str, payload: ReviewDecision) -> dict:
    if not db.get_claim(claim_id):
        raise HTTPException(status_code=404, detail="Claim not found")
    note_id = db.add_reviewer_note(claim_id, payload.reviewer, payload.decision, payload.comments, payload.request_more_evidence)
    db.update_claim_status(claim_id, "HUMAN_REVIEW")
    return {"status": "success", "note_id": note_id, "message": "Reviewer decision recorded", "disclaimer": DISCLAIMER}


@app.get("/api/edge-cases")
def edge_cases() -> dict:
    return {
        "status": "success",
        "edge_case_testing_mode": True,
        "scenarios": [
            "valid claim", "expired policy", "expired licence", "invalid/altered RC", "RC/image mismatch",
            "policy/image mismatch", "different vehicle images", "duplicate/reused images", "AI-generated or AI-edited concern",
            "manipulated damage", "pre-existing damage", "insufficient/blurry/dark images", "multiple vehicles",
            "non-car image", "corrupted file", "screenshot/downloaded image", "impossible timestamp",
            "location mismatch", "accident-description mismatch", "severe/hidden damage", "multiple damage types",
            "duplicate damage across angles", "missing documents", "low OCR confidence", "suspicious document",
            "duplicate invoice", "excessive estimate", "contradictory evidence", "low AI confidence",
        ],
        "expected_behavior": "Each scenario should produce VERIFIED/ELIGIBLE, NEEDS_VERIFICATION, NOT_ELIGIBLE, or SUSPICIOUS_EVIDENCE without crashing.",
        "disclaimer": DISCLAIMER,
    }

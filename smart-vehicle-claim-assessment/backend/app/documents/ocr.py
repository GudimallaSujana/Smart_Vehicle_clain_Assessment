from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image, ImageOps

from app.documents.extraction import clean_text, extract_fields

try:
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover
    PdfReader = None

try:
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover
    pytesseract = None


SUPPORTED_OCR = ["pypdf_text_extraction", "pytesseract_if_installed"]


def ocr_availability() -> Dict[str, Any]:
    tesseract_binary = False
    try:
        res = subprocess.run(["tesseract", "--version"], capture_output=True, text=True, timeout=2)
        tesseract_binary = res.returncode == 0
    except Exception:
        tesseract_binary = False
    return {
        "pypdf_available": PdfReader is not None,
        "pytesseract_package_available": pytesseract is not None,
        "tesseract_binary_available": tesseract_binary,
        "image_ocr_available": bool(pytesseract is not None and tesseract_binary),
        "engines": SUPPORTED_OCR,
    }


def _extract_pdf_text(path: Path) -> Dict[str, Any]:
    warnings: List[str] = []
    text = ""
    confidence: Optional[float] = None
    if PdfReader is not None:
        try:
            reader = PdfReader(str(path))
            for page in reader.pages[:20]:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
            if text.strip():
                confidence = 0.85
        except Exception as exc:
            warnings.append(f"PDF text extraction failed ({type(exc).__name__}); attempting safe byte-text fallback.")
    if not text.strip():
        try:
            raw = path.read_bytes()
            # Useful for test/demo PDFs and some simple generated PDFs. Not a substitute for OCR.
            text = raw.decode("utf-8", errors="ignore")
            confidence = 0.35 if text.strip() else 0.0
            warnings.append("PDF may be scanned or malformed; OCR/manual correction may be required.")
        except Exception:
            confidence = 0.0
            warnings.append("PDF could not be read.")
    return {"text": clean_text(text), "ocr_confidence": confidence, "warnings": warnings, "engine": "pypdf_or_pdf_byte_fallback"}


def _extract_image_text(path: Path) -> Dict[str, Any]:
    availability = ocr_availability()
    warnings: List[str] = []
    if not availability["image_ocr_available"]:
        return {
            "text": "",
            "ocr_confidence": 0.0,
            "warnings": ["Image OCR engine is not available. Install Tesseract or EasyOCR and reprocess, or manually enter/correct fields."],
            "engine": "ocr_unavailable",
        }
    try:
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        text = pytesseract.image_to_string(img) if pytesseract is not None else ""
        confidence = None
        try:
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)  # type: ignore[union-attr]
            confs = [float(c) for c in data.get("conf", []) if str(c).strip() not in {"-1", ""}]
            confidence = round(sum(confs) / (100 * len(confs)), 2) if confs else 0.4
        except Exception:
            confidence = 0.45 if text.strip() else 0.0
        return {"text": clean_text(text), "ocr_confidence": confidence, "warnings": warnings, "engine": "pytesseract"}
    except Exception as exc:
        return {"text": "", "ocr_confidence": 0.0, "warnings": [f"OCR failed: {type(exc).__name__}."], "engine": "pytesseract"}


def process_document(path: str | Path, document_type: str) -> Dict[str, Any]:
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".pdf":
        result = _extract_pdf_text(path)
    elif ext in {".jpg", ".jpeg", ".png"}:
        result = _extract_image_text(path)
    else:
        result = {"text": "", "ocr_confidence": 0.0, "warnings": ["Unsupported document type."], "engine": "none"}
    fields = extract_fields(result.get("text") or "", document_type=document_type)
    verification_status = "EXTRACTED" if fields.get("raw_text_available") else "OCR_FAILED_OR_EMPTY"
    if (result.get("ocr_confidence") or 0) < 0.55:
        verification_status = "NEEDS_USER_REVIEW"
    return {
        "extracted_text": result.get("text") or "",
        "extracted_fields": fields,
        "ocr_confidence": result.get("ocr_confidence"),
        "warnings": result.get("warnings") or [],
        "engine": result.get("engine"),
        "verification_status": verification_status,
    }

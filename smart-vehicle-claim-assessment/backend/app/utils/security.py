from __future__ import annotations

import hashlib
import re
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO, Dict, Tuple

from PIL import Image, UnidentifiedImageError

from app.config import get_settings

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
IMAGE_MIME_BY_EXT = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
DOC_MIME_BY_EXT = {**IMAGE_MIME_BY_EXT, ".pdf": "application/pdf"}


class UploadValidationError(ValueError):
    pass


def sanitize_filename(filename: str) -> str:
    stem = Path(filename or "upload").stem
    suffix = Path(filename or "").suffix.lower()
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._")[:80] or "upload"
    return f"{safe_stem}_{uuid.uuid4().hex[:10]}{suffix}"


def secure_path(base: Path, filename: str) -> Path:
    base = base.resolve()
    target = (base / filename).resolve()
    if not str(target).startswith(str(base)):
        raise UploadValidationError("Unsafe filename/path traversal detected.")
    return target


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _check_size(path: Path, max_mb: int) -> None:
    size = path.stat().st_size
    if size <= 0:
        raise UploadValidationError("The uploaded file is empty. Please upload a valid file.")
    if size > max_mb * 1024 * 1024:
        raise UploadValidationError(f"The uploaded file is too large. Maximum allowed size is {max_mb} MB.")


def _validate_image_content(path: Path) -> Dict[str, str]:
    try:
        with Image.open(path) as img:
            img.verify()
        with Image.open(path) as img:
            return {"format": img.format or "UNKNOWN", "width": str(img.width), "height": str(img.height)}
    except UnidentifiedImageError as exc:
        raise UploadValidationError("The image appears corrupted or is not a supported image file.") from exc
    except Exception as exc:
        raise UploadValidationError("The image could not be read. Please upload a clear JPG or PNG image.") from exc


def _validate_pdf_content(path: Path) -> None:
    with path.open("rb") as f:
        header = f.read(8)
    if not header.startswith(b"%PDF"):
        raise UploadValidationError("The PDF appears corrupted or is not a valid PDF file.")


def save_upload(fileobj: BinaryIO, original_filename: str, claim_id: str, category: str) -> Tuple[Path, str, Dict[str, str]]:
    """Save an uploaded stream after validating filename, size and content.

    category must be either 'image' or 'document'. File extension is checked and
    the file content is inspected. Extension alone is never trusted.
    """

    settings = get_settings()
    ext = Path(original_filename or "").suffix.lower()
    if category == "image":
        allowed = ALLOWED_IMAGE_EXTENSIONS
        mime_lookup = IMAGE_MIME_BY_EXT
        max_mb = settings.max_image_mb
    else:
        allowed = ALLOWED_DOCUMENT_EXTENSIONS
        mime_lookup = DOC_MIME_BY_EXT
        max_mb = settings.max_document_mb

    if ext not in allowed:
        raise UploadValidationError(f"Unsupported file format '{ext}'. Supported formats: {', '.join(sorted(allowed))}.")

    target_dir = settings.upload_dir / claim_id / category
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_filename(original_filename)
    target = secure_path(target_dir, safe_name)
    with target.open("wb") as out:
        shutil.copyfileobj(fileobj, out)

    _check_size(target, max_mb)
    metadata: Dict[str, str] = {}
    if category == "image" or ext in ALLOWED_IMAGE_EXTENSIONS:
        metadata.update(_validate_image_content(target))
    elif ext == ".pdf":
        _validate_pdf_content(target)
        metadata["format"] = "PDF"

    return target, mime_lookup.get(ext, "application/octet-stream"), metadata

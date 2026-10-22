from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

try:  # OpenCV is optional in core development.
    import cv2  # type: ignore
except Exception:  # pragma: no cover - exercised only when cv2 unavailable
    cv2 = None

from app.utils.security import sha256_file


MIN_WIDTH = 640
MIN_HEIGHT = 360
BLUR_WARN_THRESHOLD = 75.0
BLUR_FAIL_THRESHOLD = 35.0
DARK_WARN_THRESHOLD = 55.0
BRIGHT_WARN_THRESHOLD = 220.0


def average_hash(image: Image.Image, hash_size: int = 8) -> str:
    gray = ImageOps.grayscale(image).resize((hash_size, hash_size), Image.Resampling.LANCZOS)
    pixels = np.asarray(gray, dtype=np.float32)
    avg = pixels.mean()
    bits = pixels > avg
    value = 0
    for bit in bits.flatten():
        value = (value << 1) | int(bool(bit))
    return f"{value:0{hash_size * hash_size // 4}x}"


def hamming_hash(a: str, b: str) -> int:
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except Exception:
        return 64


def _blur_score(gray: np.ndarray) -> float:
    if cv2 is not None:
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    # Fallback: high-frequency energy approximation using adjacent-pixel differences.
    gx = np.diff(gray.astype(np.float32), axis=1)
    gy = np.diff(gray.astype(np.float32), axis=0)
    return float((gx.var() + gy.var()) / 2.0)


def inspect_image_quality(path: str | Path) -> Dict[str, Any]:
    path = Path(path)
    warnings: List[str] = []
    errors: List[str] = []
    try:
        with Image.open(path) as raw:
            img = ImageOps.exif_transpose(raw).convert("RGB")
            width, height = img.size
            gray = np.asarray(ImageOps.grayscale(img), dtype=np.uint8)
            brightness = float(gray.mean())
            blur = _blur_score(gray)
            phash = average_hash(img)
            sha = sha256_file(path)
            orientation_corrected = raw.size != img.size or raw.getexif().get(274) is not None
            megapixels = round((width * height) / 1_000_000, 3)
    except UnidentifiedImageError:
        return {
            "status": "FAIL",
            "can_continue": False,
            "errors": ["The uploaded image is corrupted or unsupported."],
            "warnings": [],
        }
    except Exception as exc:
        return {
            "status": "FAIL",
            "can_continue": False,
            "errors": [f"The uploaded image could not be processed: {type(exc).__name__}."],
            "warnings": [],
        }

    if width < MIN_WIDTH or height < MIN_HEIGHT:
        warnings.append(f"Resolution is low ({width}×{height}). Upload a wider full-vehicle image if possible.")
    if blur < BLUR_FAIL_THRESHOLD:
        errors.append("Image is too blurry for reliable assessment. Please upload a sharper image.")
    elif blur < BLUR_WARN_THRESHOLD:
        warnings.append("Image appears somewhat blurry; manual verification may be required.")
    if brightness < DARK_WARN_THRESHOLD:
        warnings.append("Image appears dark/underexposed; use better lighting if possible.")
    elif brightness > BRIGHT_WARN_THRESHOLD:
        warnings.append("Image appears overexposed/too bright; details may be missing.")

    status = "FAIL" if errors else ("WARN" if warnings else "PASS")
    return {
        "status": status,
        "can_continue": not errors,
        "width": width,
        "height": height,
        "megapixels": megapixels,
        "brightness": round(brightness, 2),
        "blur_score": round(blur, 2),
        "sha256": sha,
        "perceptual_hash": phash,
        "orientation_corrected": orientation_corrected,
        "warnings": warnings,
        "errors": errors,
        "quality_method": "PIL + Laplacian variance" if cv2 is not None else "PIL + high-frequency variance fallback",
    }

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

from app.config import get_settings

KAGGLE_DAMAGE_CLASSES = ["crack", "scratch", "tire flat", "dent", "glass shatter", "lamp broken"]
SEVERITY_ORDER = {"Unknown": 0, "Minor": 1, "Moderate": 2, "Severe": 3}
COMPONENTS_BY_REGION = {
    "front": ["front bumper", "bonnet", "headlight", "grille", "windshield"],
    "rear": ["rear bumper", "tail light", "boot", "rear windshield"],
    "side": ["door", "fender", "side mirror", "wheel area", "roof"],
    "closeup": ["damaged area"],
    "unknown": ["visible exterior panel"],
}


def get_device_info() -> Dict[str, Any]:
    try:
        import torch  # type: ignore

        cuda = bool(torch.cuda.is_available())
        return {
            "torch_available": True,
            "cuda_available": cuda,
            "device": "cuda" if cuda else "cpu",
            "gpu_name": torch.cuda.get_device_name(0) if cuda else None,
        }
    except Exception:
        return {"torch_available": False, "cuda_available": False, "device": "cpu", "gpu_name": None}


def model_status() -> Dict[str, Any]:
    settings = get_settings()
    weights = settings.yolo_weights_path
    available = bool(weights and Path(weights).exists())
    return {
        "strategy": "ultralytics_yolo_if_configured_else_documented_heuristic_fallback",
        "model_available": available,
        "weights_path": weights if available else None,
        "fallback_active": not available,
        "supported_dataset_damage_classes": KAGGLE_DAMAGE_CLASSES,
        "component_detection": "No trained component detector is bundled; components are inferred from image region/view in fallback mode.",
    }


def _damage_mask(img: Image.Image) -> np.ndarray:
    arr = np.asarray(img.convert("RGB"), dtype=np.uint8)
    gray = np.asarray(ImageOps.grayscale(img), dtype=np.uint8)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    # Synthetic/demo damage and many real paint-transfer/scratch marks often appear
    # as localized red/brown/dark anomalies. Prefer these localized anomalies when
    # present so we do not treat normal vehicle/wheel/body edges as damage.
    red_brown = ((r.astype(np.int16) > g.astype(np.int16) + 25) & (r.astype(np.int16) > b.astype(np.int16) + 25) & (r > 80) & (g < 140) & (b < 140))
    if cv2 is not None:
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 60, 150)
        if int(red_brown.sum()) > 60:
            focus = cv2.dilate(red_brown.astype(np.uint8) * 255, np.ones((21, 21), np.uint8), iterations=1)
            mask = cv2.bitwise_or(red_brown.astype(np.uint8) * 255, cv2.bitwise_and(edges, focus))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8), iterations=2)
            return mask > 0
        # Generic fallback when no color anomaly exists. Keep only smaller, local high-gradient/dark clusters.
        dark = (gray < np.percentile(gray, 7)).astype(np.uint8) * 255
        mask = cv2.bitwise_or(edges, dark)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)
        return mask > 0
    # Numpy fallback: color anomaly if present, otherwise gradient magnitude + very dark pixels.
    if int(red_brown.sum()) > 60:
        return red_brown
    gray_f = gray.astype(np.float32)
    gx = np.zeros_like(gray_f)
    gy = np.zeros_like(gray_f)
    gx[:, 1:] = np.abs(gray_f[:, 1:] - gray_f[:, :-1])
    gy[1:, :] = np.abs(gray_f[1:, :] - gray_f[:-1, :])
    grad = gx + gy
    return (grad > np.percentile(grad, 98)) | (gray < np.percentile(gray, 7))


def _components(mask: np.ndarray, min_area: int, max_count: int = 5) -> List[Tuple[int, int, int, int, int]]:
    h, w = mask.shape[:2]
    if cv2 is not None:
        num, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
        boxes = []
        for idx in range(1, num):
            x, y, bw, bh, area = stats[idx]
            too_global = bw > 0.65 * w or bh > 0.55 * h or area > 0.12 * w * h
            if area >= min_area and bw >= 12 and bh >= 8 and not too_global:
                boxes.append((int(x), int(y), int(bw), int(bh), int(area)))
        boxes.sort(key=lambda b: b[4], reverse=True)
        return boxes[:max_count]
    ys, xs = np.where(mask)
    if len(xs) < min_area:
        return []
    x1, x2 = int(xs.min()), int(xs.max())
    y1, y2 = int(ys.min()), int(ys.max())
    area = int(mask.sum())
    return [(x1, y1, x2 - x1, y2 - y1, area)]


def _infer_damage_type(box: Tuple[int, int, int, int, int], image_shape: Tuple[int, int], img: Image.Image) -> str:
    x, y, w, h, area = box
    aspect = w / max(h, 1)
    area_ratio = area / max(image_shape[0] * image_shape[1], 1)
    crop = np.asarray(ImageOps.grayscale(img.crop((x, y, x + w, y + h))), dtype=np.uint8)
    contrast = float(crop.std()) if crop.size else 0.0
    if aspect > 4.0 or (area_ratio < 0.004 and contrast > 35):
        return "scratch"
    if aspect < 0.35 and area_ratio < 0.008:
        return "crack"
    if contrast > 55 and area_ratio > 0.01:
        return "dent"
    if area_ratio > 0.035:
        return "dent"
    return "scratch"


def _infer_component(view_type: Optional[str], box: Tuple[int, int, int, int, int], image_size: Tuple[int, int]) -> str:
    view = (view_type or "unknown").lower()
    width, height = image_size
    x, y, w, h, _ = box
    cx = (x + w / 2) / max(width, 1)
    cy = (y + h / 2) / max(height, 1)
    if "front" in view:
        if cy > 0.65:
            return "front bumper"
        if cy < 0.32:
            return "bonnet" if 0.2 < cx < 0.8 else "headlight"
        if cx < 0.25 or cx > 0.75:
            return "headlight"
        return "grille"
    if "rear" in view:
        if cy > 0.65:
            return "rear bumper"
        if cx < 0.25 or cx > 0.75:
            return "tail light"
        return "boot"
    if "side" in view or "left" in view or "right" in view:
        if cy > 0.72:
            return "wheel area"
        if cx < 0.22 or cx > 0.78:
            return "fender"
        if cy < 0.28:
            return "roof"
        return "door"
    if "close" in view or "damage" in view:
        return "damaged area"
    # Generic region mapping, explicitly labelled as inferred.
    if cy > 0.72:
        return "bumper / lower panel"
    if cy < 0.28:
        return "bonnet / windshield area"
    return "door / side panel area"


def _severity(box: Tuple[int, int, int, int, int], image_shape: Tuple[int, int], damage_type: str, confidence: float, quality_status: str) -> Tuple[str, str, float]:
    h, w = image_shape
    area_ratio = box[4] / max(w * h, 1)
    score = area_ratio * 100.0
    if damage_type in {"glass shatter", "lamp broken"}:
        score += 1.5
    elif damage_type == "dent":
        score += 0.8
    if confidence < 0.32 or quality_status == "FAIL":
        return "Unknown", "Evidence/model confidence is insufficient; route to manual inspection.", score
    if score < 0.8:
        return "Minor", "Small visible damaged area relative to image; no severe structural indicators detected by fallback.", score
    if score < 3.5:
        return "Moderate", "Visible damage occupies a moderate region and/or includes dent-like deformation.", score
    return "Severe", "Large visible damaged area. External photos cannot estimate hidden/internal damage; manual inspection required.", score


def _confidence(box: Tuple[int, int, int, int, int], image_shape: Tuple[int, int], img: Image.Image, quality_status: str) -> float:
    h, w = image_shape
    area_ratio = box[4] / max(w * h, 1)
    x, y, bw, bh, _ = box
    crop = np.asarray(ImageOps.grayscale(img.crop((x, y, x + bw, y + bh))), dtype=np.uint8)
    contrast = float(crop.std()) if crop.size else 0.0
    conf = 0.18 + min(area_ratio * 8.0, 0.22) + min(contrast / 255.0, 0.22)
    if quality_status == "WARN":
        conf -= 0.08
    if quality_status == "FAIL":
        conf -= 0.18
    # Heuristic fallback must not look like a validated production model.
    return round(max(0.05, min(conf, 0.62)), 3)


def _draw_overlay(img: Image.Image, detections: List[Dict[str, Any]], out_path: Path) -> None:
    vis = img.convert("RGB").copy()
    draw = ImageDraw.Draw(vis)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
    for det in detections:
        x, y, w, h = det["bbox"]
        label = f"{det['damage_type']} | {det['damaged_part']} | {det['severity']} | {det['confidence']:.2f}"
        colour = (220, 38, 38) if det["severity"] == "Severe" else (245, 158, 11) if det["severity"] == "Moderate" else (16, 185, 129)
        draw.rectangle([x, y, x + w, y + h], outline=colour, width=4)
        # label background
        text_box = draw.textbbox((x, max(0, y - 22)), label, font=font)
        draw.rectangle(text_box, fill=colour)
        draw.text((x, max(0, y - 22)), label, fill=(255, 255, 255), font=font)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    vis.save(out_path)


def _human_damage_explanation(component: str, damage_type: str, severity: str, confidence: float, view_type: Optional[str], severity_explanation: str) -> str:
    part = (component or "visible exterior panel").lower()
    if "headlight" in part or "lamp" in part:
        detail = "Check lens surface, mounting tabs and lamp alignment."
    elif "bumper" in part:
        detail = "Check bumper cover, clips, brackets and paint transfer."
    elif "bonnet" in part or "hood" in part:
        detail = "Check panel gap, hood edge and latch alignment."
    elif "tail" in part or "rear" in part or "boot" in part:
        detail = "Rear-area signal; verify against rear-view evidence before inclusion."
    elif "fender" in part or "wheel" in part:
        detail = "Check wheel-arch edge, side panel scuffs and local denting."
    elif "damage" in part:
        detail = "Close-up signal; map it to the exact component."
    else:
        detail = "Inspect the exact panel location and confirm repair scope."
    return f"{component}: {severity.lower()} {damage_type} signal. {detail}"

def analyze_single_image(image_record: Dict[str, Any]) -> Dict[str, Any]:
    settings = get_settings()
    path = Path(image_record["stored_path"])
    quality = image_record.get("quality_json") or {}
    quality_status = quality.get("status", "WARN")
    with Image.open(path) as raw:
        img = ImageOps.exif_transpose(raw).convert("RGB")
        # Limit huge images to keep CPU mode practical.
        max_side = 1280
        if max(img.size) > max_side:
            img.thumbnail((max_side, max_side))
        mask = _damage_mask(img)
        min_area = max(80, int(img.size[0] * img.size[1] * 0.001))
        boxes = _components(mask, min_area=min_area)
        detections: List[Dict[str, Any]] = []
        for box in boxes:
            damage_type = _infer_damage_type(box, mask.shape, img)
            confidence = _confidence(box, mask.shape, img, quality_status)
            severity, sev_expl, score = _severity(box, mask.shape, damage_type, confidence, quality_status)
            component = _infer_component(image_record.get("view_type"), box, img.size)
            x, y, w, h, area = box
            detections.append(
                {
                    "image_id": image_record.get("image_id"),
                    "bbox": [x, y, w, h],
                    "damage_area_pixels": int(area),
                    "damage_area_ratio": round(area / max(mask.shape[0] * mask.shape[1], 1), 5),
                    "damage_type": damage_type,
                    "damaged_part": component,
                    "severity": severity,
                    "severity_score": round(score, 3),
                    "confidence": confidence,
                    "method": "heuristic_fallback_not_a_validated_trained_detector",
                    "explanation": _human_damage_explanation(component, damage_type, severity, confidence, image_record.get("view_type"), sev_expl),
                }
            )
        if not detections:
            explanation = "No visible damage region was detected by the fallback analyzer. This is not proof of no damage."
        else:
            explanation = f"Detected {len(detections)} candidate damaged region(s) using CPU fallback heuristics."
        overlay_path = settings.overlay_dir / f"{image_record['image_id']}_overlay.jpg"
        _draw_overlay(img, detections, overlay_path)
    return {
        "image_id": image_record.get("image_id"),
        "view_type": image_record.get("view_type"),
        "detections": detections,
        "overlay_path": str(overlay_path),
        "explanation": explanation,
        "model_status": model_status(),
        "warnings": [
            "Fallback CV mode is for demo/decision-support only and is not an experimentally evaluated damage detector."
        ],
    }


def aggregate_assessments(image_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate image-level findings while avoiding obvious duplicate components.

    Duplicate suppression groups by damaged part + damage type and keeps the highest
    severity/confidence observation. This is a conservative baseline because a real
    multi-view 3D association model is not bundled.
    """

    grouped: Dict[Tuple[str, str], Dict[str, Any]] = {}
    raw_count = 0
    for result in image_results:
        for det in result.get("detections", []):
            raw_count += 1
            key = (det.get("damaged_part", "unknown"), det.get("damage_type", "unknown"))
            current = grouped.get(key)
            if current is None:
                grouped[key] = det
            else:
                if SEVERITY_ORDER.get(det.get("severity", "Unknown"), 0) > SEVERITY_ORDER.get(current.get("severity", "Unknown"), 0) or det.get("confidence", 0) > current.get("confidence", 0):
                    grouped[key] = det
    assessments = []
    for det in grouped.values():
        assessments.append(
            {
                "image_id": det.get("image_id"),
                "damaged_part": det.get("damaged_part"),
                "damage_type": det.get("damage_type"),
                "severity": det.get("severity"),
                "confidence": det.get("confidence"),
                "damage_area": {
                    "bbox": det.get("bbox"),
                    "area_ratio": det.get("damage_area_ratio"),
                    "method": det.get("method"),
                },
                "explanation": det.get("explanation"),
            }
        )
    overall = "Unknown"
    for a in assessments:
        if SEVERITY_ORDER.get(a.get("severity", "Unknown"), 0) > SEVERITY_ORDER.get(overall, 0):
            overall = a.get("severity", "Unknown")
    return {
        "raw_detection_count": raw_count,
        "deduplicated_damage_count": len(assessments),
        "assessments": assessments,
        "overall_severity": overall,
        "deduplication_note": "Grouped by inferred component and damage type to avoid obvious double counting across multiple views.",
    }

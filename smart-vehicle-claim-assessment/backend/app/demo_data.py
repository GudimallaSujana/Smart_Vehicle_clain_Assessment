from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from PIL import Image, ImageDraw, ImageFont

from app.config import get_settings


def _draw_demo_car(path: Path, view: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    w, h = 1000, 620
    img = Image.new("RGB", (w, h), (239, 246, 255))
    draw = ImageDraw.Draw(img)
    # soft road/card background
    draw.rounded_rectangle((60, 420, 940, 520), radius=30, fill=(203, 213, 225))
    # vehicle body
    draw.rounded_rectangle((150, 230, 850, 420), radius=45, fill=(37, 99, 235), outline=(30, 64, 175), width=4)
    draw.polygon([(290, 230), (390, 125), (610, 125), (720, 230)], fill=(59, 130, 246), outline=(30, 64, 175))
    draw.polygon([(405, 145), (465, 145), (460, 220), (345, 220)], fill=(219, 234, 254))
    draw.polygon([(485, 145), (595, 145), (665, 220), (490, 220)], fill=(219, 234, 254))
    draw.ellipse((220, 375, 340, 495), fill=(15, 23, 42))
    draw.ellipse((660, 375, 780, 495), fill=(15, 23, 42))
    draw.ellipse((250, 405, 310, 465), fill=(148, 163, 184))
    draw.ellipse((690, 405, 750, 465), fill=(148, 163, 184))
    draw.rectangle((150, 330, 215, 365), fill=(250, 204, 21))
    draw.rectangle((785, 330, 850, 365), fill=(254, 226, 226))
    draw.text((440, 360), "TS09AB1234", fill=(15, 23, 42))
    # damage: red/brown dent/scratch cluster on front-left bumper/door area.
    if view in {"front", "closeup"}:
        draw.ellipse((165, 300, 315, 405), outline=(127, 29, 29), width=9)
        for i in range(7):
            x0 = 185 + i * 17
            draw.line((x0, 315 + (i % 2) * 15, x0 + 90, 355 + (i % 3) * 12), fill=(69, 10, 10), width=5)
        draw.polygon([(195, 380), (245, 330), (310, 370), (270, 400)], outline=(239, 68, 68), width=5)
    if view == "side":
        draw.ellipse((360, 305, 520, 395), outline=(127, 29, 29), width=8)
        draw.line((380, 330, 500, 360), fill=(69, 10, 10), width=5)
    draw.text((70, 60), f"Demo Data — Not a Real Insurance Claim ({view})", fill=(30, 41, 59))
    img.save(path)


def _write_demo_pdf(path: Path, kind: str) -> None:
    # A simple text-containing pseudo-PDF valid enough for our PDF header validator and byte fallback.
    # It is intentionally demo-only; real PDFs are handled with pypdf/OCR where available.
    if kind == "policy":
        text = """Policy Number: DEMO-POL-2026
Vehicle Registration Number: TS09AB1234
Policy Type: Comprehensive / Package Policy
Policy Start Date: 01/01/2026
Policy End Date: 31/12/2026
IDV: Rs. 500000
Deductible: Rs. 1000
Coverage: Own Damage, Accidental external damage
Exclusions: Wear and tear; Mechanical breakdown not arising from accident
"""
    elif kind == "rc":
        text = """Registration Certificate
Registration Number: TS09AB1234
Owner Name: Demo Vehicle Owner
Make: DemoMake
Model: DemoModel
Manufacturing Year: 2021
Colour: Blue
"""
    else:
        text = """Repair Estimate
Vehicle Registration Number: TS09AB1234
Garage: Demo Workshop Hyderabad
Estimate Date: 22/09/2026
Total: Rs. 12500
"""
    content = f"%PDF-1.4\n% Demo text PDF for local testing only\n{text}\n%%EOF\n"
    path.write_text(content, encoding="utf-8")


def ensure_demo_assets() -> Dict[str, List[Dict[str, str]]]:
    settings = get_settings()
    sample_dir = settings.data_dir / "sample"
    sample_dir.mkdir(parents=True, exist_ok=True)
    images = []
    for view in ["front", "side", "closeup"]:
        path = sample_dir / f"demo_accident_{view}.png"
        if not path.exists():
            _draw_demo_car(path, view)
        images.append({"path": str(path), "view_type": view})
    documents = []
    for kind, doc_type in [("policy", "policy"), ("rc", "rc"), ("repair_estimate", "repair_estimate")]:
        path = sample_dir / f"demo_{kind}.pdf"
        if not path.exists():
            _write_demo_pdf(path, kind)
        documents.append({"path": str(path), "document_type": doc_type})
    readme = sample_dir / "README.md"
    if not readme.exists():
        readme.write_text("# Demo Data\n\nSynthetic sample images/documents for Demo Mode only. Not real claims, not real prices, and not evaluation data.\n", encoding="utf-8")
    return {"images": images, "documents": documents}

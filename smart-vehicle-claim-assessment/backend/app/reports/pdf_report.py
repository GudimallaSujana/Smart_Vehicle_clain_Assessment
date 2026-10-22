from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.config import get_settings
from app.schemas import DISCLAIMER

try:
    from reportlab.lib import colors  # type: ignore
    from reportlab.lib.pagesizes import A4  # type: ignore
    from reportlab.lib.styles import getSampleStyleSheet  # type: ignore
    from reportlab.lib.units import cm  # type: ignore
    from reportlab.platypus import Image as RLImage  # type: ignore
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # type: ignore
except Exception:  # pragma: no cover
    colors = None
    A4 = None
    getSampleStyleSheet = None
    cm = None
    RLImage = None
    Paragraph = None
    SimpleDocTemplate = None
    Spacer = None
    Table = None
    TableStyle = None


def _money(value: Any) -> str:
    if value is None:
        return "Not available"
    try:
        return "₹{:,.0f}".format(float(value))
    except Exception:
        return str(value)


def _p(text: str, style) -> Any:
    return Paragraph(html.escape(str(text)).replace("\n", "<br/>"), style)


def generate_claim_report(claim: Dict[str, Any]) -> Path:
    settings = get_settings()
    settings.report_dir.mkdir(parents=True, exist_ok=True)
    out = settings.report_dir / f"{claim['claim_id']}_preliminary_report.pdf"
    if SimpleDocTemplate is None:
        _minimal_pdf(out, claim)
        return out

    styles = getSampleStyleSheet()
    story: List[Any] = []
    story.append(_p("AI-Based Smart Vehicle Claim Assessment", styles["Title"]))
    story.append(_p("Preliminary Claim Assessment Report", styles["Heading2"]))
    story.append(_p(DISCLAIMER, styles["BodyText"]))
    story.append(Spacer(1, 0.3 * cm))

    vehicle = claim.get("vehicle") or {}
    policy = claim.get("policy") or {}
    estimation = claim.get("estimation") or {}

    sections = [
        ("1. Claim Information", [["Claim ID", claim.get("claim_id")], ["Status", claim.get("claim_status")], ["Eligibility", claim.get("eligibility")], ["Demo Mode", "Yes - Demo Data" if claim.get("demo_mode") else "No"]]),
        ("2. Vehicle Information", [["Registration Number", vehicle.get("registration_number")], ["Make/Model", f"{vehicle.get('make') or ''} {vehicle.get('model') or ''}".strip()], ["Year", vehicle.get("year")], ["Colour", vehicle.get("colour")]]),
        ("3. Accident Information", [["Accident Date", claim.get("accident_date")], ["Claim Date", claim.get("claim_date")], ["Location", claim.get("accident_location")], ["Description", claim.get("accident_description")]]),
        ("6. Extracted Policy Information", [["Policy Number", policy.get("policy_number")], ["Policy Type", policy.get("policy_type")], ["Start Date", policy.get("start_date")], ["End Date", policy.get("end_date")], ["IDV", _money(policy.get("idv"))], ["Deductible", _money(policy.get("deductible"))]]),
        ("8. Preliminary Repair Estimate", [["Repair Cost", _money(estimation.get("repair_cost"))], ["Deductible", _money(estimation.get("deductible"))], ["Preliminary Settlement", _money(estimation.get("estimated_settlement"))], ["Source", estimation.get("source")], ["Status", estimation.get("status")]]),
    ]
    for title, rows in sections:
        story.append(_p(title, styles["Heading2"]))
        story.append(_table(rows))
        story.append(Spacer(1, 0.2 * cm))

    story.append(_p("4. Uploaded Evidence", styles["Heading2"]))
    for image in claim.get("images") or []:
        story.append(_p(f"Image: {image.get('original_filename')} | View: {image.get('view_type')} | Validation: {image.get('validation_status')}", styles["BodyText"]))
        overlay = image.get("overlay_path") or image.get("stored_path")
        try:
            if overlay and Path(overlay).exists():
                story.append(RLImage(overlay, width=10 * cm, height=6 * cm))
        except Exception:
            pass
        story.append(Spacer(1, 0.15 * cm))

    story.append(_p("5. AI Damage Findings", styles["Heading2"]))
    damage_rows = [["Part", "Damage Type", "Severity", "Confidence", "Explanation"]]
    for d in claim.get("damage_assessments") or []:
        damage_rows.append([d.get("damaged_part"), d.get("damage_type"), d.get("severity"), d.get("confidence"), (d.get("explanation") or "")[:160]])
    story.append(_table(damage_rows, header=True))

    story.append(_p("7. Policy Analysis", styles["Heading2"]))
    policy_json = claim.get("policy_json") or {}
    factor_rows = [["Factor", "Evidence", "Effect", "Status"]]
    for f in policy_json.get("factors", []):
        factor_rows.append([f.get("factor"), f.get("evidence"), f.get("effect"), f.get("status")])
    story.append(_table(factor_rows, header=True))

    story.append(_p("10. Explanation and Validation Warnings", styles["Heading2"]))
    checks = claim.get("verification_checks") or []
    check_rows = [["Check", "Status", "Explanation", "Recommended action"]]
    for c in checks:
        check_rows.append([c.get("check_name"), c.get("status"), c.get("explanation"), c.get("recommended_action")])
    story.append(_table(check_rows, header=True))

    story.append(_p("11. Limitations", styles["Heading2"]))
    story.append(_p("External photographs cannot reliably assess hidden/internal mechanical damage. Fallback computer-vision mode is not a validated production model. OCR can make mistakes and must be reviewed by the user/claim team. Insurer-specific policy wording must be configured or verified manually.", styles["BodyText"]))
    story.append(_p("12. Disclaimer", styles["Heading2"]))
    story.append(_p("This report is an AI-assisted preliminary assessment generated from the information and images provided. It does not constitute final claim approval, insurance advice, or a binding settlement. Final assessment is subject to verification by the respective insurer, policy terms, documentation, inspection, and applicable regulations.", styles["BodyText"]))

    doc = SimpleDocTemplate(str(out), pagesize=A4, rightMargin=1.5 * cm, leftMargin=1.5 * cm, topMargin=1.2 * cm, bottomMargin=1.2 * cm)
    doc.build(story)
    return out


def _table(rows: List[List[Any]], header: bool = False) -> Any:
    style = [("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTSIZE", (0, 0), (-1, -1), 8), ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DBEAFE")))
    return Table(rows, repeatRows=1 if header else 0, style=TableStyle(style), colWidths=None)


def _minimal_pdf(out: Path, claim: Dict[str, Any]) -> None:
    # Minimal valid text-only PDF fallback when reportlab is unavailable.
    lines = [
        "AI-Based Smart Vehicle Claim Assessment",
        "Preliminary Claim Assessment Report",
        DISCLAIMER,
        f"Claim ID: {claim.get('claim_id')}",
        f"Status: {claim.get('claim_status')}",
        f"Eligibility: {claim.get('eligibility')}",
        "This is a fallback PDF because reportlab is not installed.",
    ]
    text = "\\n".join(lines).replace("(", "[").replace(")", "]")
    stream = f"BT /F1 12 Tf 72 760 Td ({text}) Tj ET"
    objects = [
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj",
        f"4 0 obj << /Length {len(stream)} >> stream\n{stream}\nendstream endobj",
        "5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
    ]
    content = "%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(content))
        content += obj + "\n"
    xref = len(content)
    content += f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n"
    for off in offsets:
        content += f"{off:010d} 00000 n \n"
    content += f"trailer << /Root 1 0 R /Size {len(objects)+1} >>\nstartxref\n{xref}\n%%EOF"
    out.write_bytes(content.encode("latin-1", errors="ignore"))

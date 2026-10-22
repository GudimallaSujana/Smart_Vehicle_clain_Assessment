from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from conftest import client


def make_test_image() -> BytesIO:
    img = Image.new("RGB", (900, 560), (240, 248, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((120, 220, 760, 390), radius=45, fill=(37, 99, 235))
    draw.ellipse((200, 350, 310, 460), fill=(15, 23, 42))
    draw.ellipse((590, 350, 700, 460), fill=(15, 23, 42))
    draw.ellipse((140, 280, 285, 375), outline=(127, 29, 29), width=8)
    draw.line((160, 300, 260, 350), fill=(69, 10, 10), width=5)
    bio = BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio


def fake_pdf(text: str) -> BytesIO:
    data = ("%PDF-1.4\n" + text + "\n%%EOF").encode("utf-8")
    return BytesIO(data)


def create_claim():
    payload = {
        "user": {"name": "Test User"},
        "vehicle": {"registration_number": "TS09AB1234", "make": "DemoMake", "model": "DemoModel", "year": 2021, "colour": "Blue"},
        "accident": {"accident_date": "2026-09-20", "claim_date": "2026-09-21", "accident_description": "front bumper collision"},
        "policy": {"policy_number": "POL12345", "policy_type": "Comprehensive / Package Policy", "start_date": "2026-01-01", "end_date": "2026-12-31", "idv": 500000, "deductible": 1000, "coverage": ["Own Damage"], "exclusions": []},
        "demo_mode": True
    }
    res = client.post("/api/claims", json=payload)
    assert res.status_code == 200, res.text
    return res.json()["claim"]


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "ml_model" in data
    assert "ocr" in data
    assert data["device"]["device"] in {"cpu", "cuda"}


def test_claim_creation():
    claim = create_claim()
    assert claim["claim_id"].startswith("CLM-")
    assert claim["vehicle"]["registration_number"] == "TS09AB1234"


def test_image_upload_validation_and_invalid_image():
    claim = create_claim()
    res = client.post(
        f"/api/claims/{claim['claim_id']}/images",
        data={"view_type": "front"},
        files={"file": ("front.png", make_test_image(), "image/png")},
    )
    assert res.status_code == 200, res.text
    assert res.json()["image"]["quality_json"]["status"] in {"PASS", "WARN"}

    bad = client.post(
        f"/api/claims/{claim['claim_id']}/images",
        data={"view_type": "front"},
        files={"file": ("bad.png", BytesIO(b"not an image"), "image/png")},
    )
    assert bad.status_code == 400
    assert "image" in bad.json()["message"].lower()


def test_document_upload_ocr_field_extraction():
    claim = create_claim()
    text = """
    Policy Number: TEST-POL-12345
    Vehicle Registration Number: TS09AB1234
    Policy Type: Comprehensive / Package Policy
    Policy Start Date: 01/01/2026
    Policy End Date: 31/12/2026
    IDV: Rs. 500000
    Deductible: Rs. 1000
    Coverage: Own Damage
    """
    res = client.post(
        f"/api/claims/{claim['claim_id']}/documents",
        data={"document_type": "policy"},
        files={"file": ("policy.pdf", fake_pdf(text), "application/pdf")},
    )
    assert res.status_code == 200, res.text
    fields = res.json()["document"]["extracted_fields"]
    assert fields["registration_number"] == "TS09AB1234"
    assert fields["policy_number"] == "TEST-POL-12345"
    assert fields["deductible"] == 1000


def test_complete_analysis_and_report_generation():
    claim = create_claim()
    # Need at least context + close-up evidence.
    for view in ["front", "closeup damage"]:
        client.post(
            f"/api/claims/{claim['claim_id']}/images",
            data={"view_type": view},
            files={"file": (f"{view}.png", make_test_image(), "image/png")},
        )
    res = client.post(f"/api/claims/{claim['claim_id']}/analyze")
    assert res.status_code == 200, res.text
    analyzed = res.json()["claim"]
    assert analyzed["eligibility"] in {"ELIGIBLE", "NEEDS_VERIFICATION", "SUSPICIOUS_EVIDENCE", "NOT_ELIGIBLE"}
    assert isinstance(analyzed["damage_assessments"], list)
    report = client.get(f"/api/claims/{claim['claim_id']}/report")
    assert report.status_code == 200
    assert report.headers["content-type"].startswith("application/pdf")
    assert len(report.content) > 100


def test_demo_seed_mode():
    res = client.post("/api/demo/seed")
    assert res.status_code == 200, res.text
    claim = res.json()["claim"]
    assert claim["demo_mode"] == 1
    assert "Demo" in res.json()["message"]

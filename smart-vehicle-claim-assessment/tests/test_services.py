from pathlib import Path

from app.documents.extraction import extract_fields
from app.estimation.estimator import estimate_cost
from app.policy.engine import analyze_policy
from app.vision.image_quality import hamming_hash
from app.vision.metrics import classification_metrics, regression_metrics


def test_ocr_field_extraction_regexes():
    text = """
    Registration Number: TS09AB1234
    Make: Tata
    Model: Nexon
    Policy Number: ABC-98765
    Policy Type: Comprehensive
    Policy Start Date: 01/04/2026
    Policy End Date: 31/03/2027
    IDV: INR 800000
    Deductible: Rs. 2000
    """
    fields = extract_fields(text, "policy")
    assert fields["registration_number"] == "TS09AB1234"
    assert fields["policy_number"] == "ABC-98765"
    assert fields["idv"] == 800000
    assert fields["deductible"] == 2000


def test_expired_policy_routes_not_eligible():
    claim = {
        "accident_date": "2026-09-20",
        "vehicle": {"registration_number": "TS09AB1234"},
        "policy": {"policy_type": "Comprehensive", "start_date": "2025-01-01", "end_date": "2025-12-31", "registration_number": "TS09AB1234", "deductible": 1000},
        "documents": [],
    }
    result = analyze_policy(claim, [])
    assert result["outcome"] == "NOT_ELIGIBLE"
    assert any(f["factor"] == "Policy validity" for f in result["factors"])


def test_registration_mismatch_suspicious_not_fraud_accusation():
    claim = {
        "accident_date": "2026-09-20",
        "vehicle": {"registration_number": "TS09AB1234"},
        "policy": {"policy_type": "Comprehensive", "start_date": "2026-01-01", "end_date": "2026-12-31", "registration_number": "MH12CD9999", "deductible": 1000},
        "documents": [],
    }
    result = analyze_policy(claim, [])
    assert result["outcome"] == "SUSPICIOUS_EVIDENCE"
    assert "fraud" not in str(result).lower()


def test_estimator_does_not_invent_prices_without_pricing_or_manual_estimate():
    claim = {"vehicle": {"make": "Unknown", "model": "Unknown"}, "policy": {"deductible": 1000}, "demo_mode": 0, "manual_repair_estimate": None}
    damages = [{"damaged_part": "front bumper", "damage_type": "dent", "severity": "Moderate"}]
    estimate = estimate_cost(claim, damages, {"merged_policy": {"deductible": 1000}})
    assert estimate["status"] == "NEEDS_PRICING_OR_MANUAL_ESTIMATE"
    assert estimate["estimated_settlement"] is None


def test_estimator_manual_estimate_settlement():
    claim = {"vehicle": {}, "policy": {"deductible": 1000}, "demo_mode": 0, "manual_repair_estimate": 12000}
    estimate = estimate_cost(claim, [], {"merged_policy": {"deductible": 1000}})
    assert estimate["repair_cost"] == 12000
    assert estimate["estimated_settlement"] == 11000


def test_metrics_helpers():
    metrics = classification_metrics(["dent", "scratch", "dent"], ["dent", "dent", "dent"])
    assert metrics["accuracy"] == 2 / 3
    reg = regression_metrics([100.0, 200.0], [110.0, 180.0])
    assert reg["mae"] == 15.0


def test_hash_distance():
    assert hamming_hash("ffff", "ffff") == 0
    assert hamming_hash("0000", "ffff") == 16

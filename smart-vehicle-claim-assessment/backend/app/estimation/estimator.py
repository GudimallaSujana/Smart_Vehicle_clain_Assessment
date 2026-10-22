from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import get_settings


def _num(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def load_pricing(demo_mode: bool = False) -> List[Dict[str, Any]]:
    settings = get_settings()
    rows: List[Dict[str, Any]] = []
    paths = [settings.data_dir / "pricing" / "pricing_template.csv"]
    if demo_mode:
        paths.append(settings.data_dir / "pricing" / "demo_pricing.csv")
    for path in paths:
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(line for line in f if not line.lstrip().startswith("#")):
                if not row.get("component") or row.get("component", "").startswith("#"):
                    continue
                for k in ["repair_cost", "replacement_cost", "labor_cost", "material_cost"]:
                    row[k] = _num(row.get(k))
                row["valid_for_demo"] = str(row.get("valid_for_demo", "")).lower() == "true"
                rows.append(row)
    return rows


def _match_price(pricing: List[Dict[str, Any]], vehicle: Dict[str, Any], component: str, damage_type: str, severity: str, demo_mode: bool) -> Optional[Dict[str, Any]]:
    make = str(vehicle.get("make") or "").lower()
    model = str(vehicle.get("model") or "").lower()
    comp = component.lower()
    dtype = damage_type.lower()
    sev = severity.lower()
    candidates = []
    for row in pricing:
        if not demo_mode and row.get("valid_for_demo"):
            continue
        row_make = str(row.get("vehicle_make") or "").lower()
        row_model = str(row.get("vehicle_model") or "").lower()
        row_component = str(row.get("component") or "").lower()
        row_dtype = str(row.get("damage_type") or "").lower()
        row_sev = str(row.get("severity") or "").lower()
        component_match = row_component == comp or row_component in comp or comp in row_component
        damage_match = row_dtype == dtype or row_dtype in dtype or dtype in row_dtype
        severity_match = not row_sev or row_sev == sev
        vehicle_match = (not row_make or row_make == make or demo_mode) and (not row_model or row_model == model or demo_mode)
        if component_match and damage_match and severity_match and vehicle_match:
            candidates.append(row)
    if candidates:
        return candidates[0]
    return None


def estimate_cost(claim: Dict[str, Any], damage_assessments: List[Dict[str, Any]], policy_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    vehicle = claim.get("vehicle") or {}
    policy = (policy_analysis or {}).get("merged_policy") or claim.get("policy") or {}
    demo_mode = bool(claim.get("demo_mode"))
    manual_estimate = _num(claim.get("manual_repair_estimate"))
    warnings: List[str] = []
    breakdown: List[Dict[str, Any]] = []

    if manual_estimate is not None and manual_estimate > 0:
        repair_cost = manual_estimate
        source = "manual_repair_estimate_upload_or_entry"
        breakdown.append(
            {
                "component": "Repair estimate document/manual entry",
                "damage_type": "documented estimate",
                "severity": "as provided",
                "repair_cost": repair_cost,
                "labor_cost": 0,
                "material_cost": 0,
                "replacement_cost": 0,
                "source": source,
                "note": "Uses user/admin-provided estimate; no spare-part price was invented.",
            }
        )
    else:
        pricing = load_pricing(demo_mode=demo_mode)
        # Deduplicate obvious repeats: component + damage type keeps highest severity already upstream.
        seen: set[Tuple[str, str]] = set()
        for damage in damage_assessments:
            component = str(damage.get("damaged_part") or "unknown")
            dtype = str(damage.get("damage_type") or "unknown")
            severity = str(damage.get("severity") or "Unknown")
            key = (component.lower(), dtype.lower())
            if key in seen:
                continue
            seen.add(key)
            price = _match_price(pricing, vehicle, component, dtype, severity, demo_mode)
            if not price:
                warnings.append(f"No configured price found for {component} / {dtype} / {severity}.")
                continue
            row_cost = sum(_num(price.get(k)) or 0 for k in ["repair_cost", "replacement_cost", "labor_cost", "material_cost"])
            breakdown.append(
                {
                    "component": component,
                    "damage_type": dtype,
                    "severity": severity,
                    "repair_cost": _num(price.get("repair_cost")) or 0,
                    "replacement_cost": _num(price.get("replacement_cost")) or 0,
                    "labor_cost": _num(price.get("labor_cost")) or 0,
                    "material_cost": _num(price.get("material_cost")) or 0,
                    "line_total": row_cost,
                    "source": price.get("source"),
                    "demo_only": bool(price.get("valid_for_demo")),
                }
            )
        repair_cost = sum(float(item.get("line_total") or item.get("repair_cost") or 0) for item in breakdown)
        source = "configured_pricing_database" if breakdown else "pricing_unavailable"
        if demo_mode and breakdown:
            warnings.append("Demo pricing used. These values are sample-only and not real Indian repair prices.")

    deductible = _num(policy.get("deductible"))
    idv = _num(policy.get("idv"))
    if repair_cost <= 0:
        return {
            "status": "NEEDS_PRICING_OR_MANUAL_ESTIMATE",
            "repair_cost": None,
            "replacement_cost": None,
            "labor_cost": None,
            "material_cost": None,
            "deductible": deductible,
            "estimated_settlement": None,
            "source": "none",
            "cost_breakdown": breakdown,
            "warnings": warnings or ["Pricing data is unavailable. Upload a repair estimate or configure pricing."],
            "explanation": "No repair cost was generated because no configured price/manual estimate was available. The system does not invent prices.",
        }

    if deductible is None:
        settlement = None
        status = "NEEDS_DEDUCTIBLE"
        warnings.append("Deductible/excess is missing; preliminary settlement cannot be calculated reliably.")
    else:
        settlement = max(repair_cost - deductible, 0)
        status = "PRELIMINARY_ESTIMATE"
        if idv is not None and settlement > idv:
            settlement = idv
            warnings.append("Settlement estimate was capped at extracted/configured IDV. Verify policy terms.")

    replacement_cost = sum(float(i.get("replacement_cost") or 0) for i in breakdown)
    labor_cost = sum(float(i.get("labor_cost") or 0) for i in breakdown)
    material_cost = sum(float(i.get("material_cost") or 0) for i in breakdown)
    return {
        "status": status,
        "repair_cost": round(repair_cost, 2),
        "replacement_cost": round(replacement_cost, 2),
        "labor_cost": round(labor_cost, 2),
        "material_cost": round(material_cost, 2),
        "deductible": deductible,
        "estimated_settlement": round(settlement, 2) if settlement is not None else None,
        "source": source,
        "cost_breakdown": breakdown,
        "warnings": warnings,
        "explanation": "Preliminary estimate = eligible configured/manual repair cost minus applicable deductible. It is not a final settlement.",
    }

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from app.config import get_settings


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"


def dumps(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, default=str)


def loads(value: Any, default: Any = None) -> Any:
    if value is None or value == "":
        return default if default is not None else {}
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default if default is not None else {}


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    settings = get_settings()
    settings.ensure_dirs()
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    out = dict(row)
    for key in [
        "metadata",
        "quality_json",
        "analysis_json",
        "extracted_fields",
        "coverage",
        "exclusions",
        "damage_area",
        "factor_json",
        "cost_breakdown",
        "validation_json",
        "policy_json",
        "claim_json",
    ]:
        if key in out:
            out[key] = loads(out[key], {} if key != "cost_breakdown" else [])
    return out


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [row_to_dict(r) or {} for r in rows]


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                contact TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS vehicles (
                vehicle_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                registration_number TEXT,
                make TEXT,
                model TEXT,
                year INTEGER,
                vehicle_value REAL,
                colour TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS policies (
                policy_id TEXT PRIMARY KEY,
                vehicle_id TEXT NOT NULL,
                policy_number TEXT,
                policy_type TEXT,
                start_date TEXT,
                end_date TEXT,
                idv REAL,
                deductible REAL,
                coverage TEXT,
                exclusions TEXT,
                source_document_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY(vehicle_id) REFERENCES vehicles(vehicle_id)
            );

            CREATE TABLE IF NOT EXISTS claims (
                claim_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                vehicle_id TEXT NOT NULL,
                policy_id TEXT,
                accident_date TEXT,
                claim_date TEXT,
                accident_location TEXT,
                accident_description TEXT,
                claim_status TEXT NOT NULL,
                eligibility TEXT,
                estimated_amount REAL,
                manual_repair_estimate REAL,
                demo_mode INTEGER DEFAULT 0,
                validation_json TEXT,
                policy_json TEXT,
                claim_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(vehicle_id) REFERENCES vehicles(vehicle_id),
                FOREIGN KEY(policy_id) REFERENCES policies(policy_id)
            );

            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL,
                document_type TEXT NOT NULL,
                original_filename TEXT,
                stored_path TEXT NOT NULL,
                mime_type TEXT,
                extracted_text TEXT,
                extracted_fields TEXT,
                verification_status TEXT,
                ocr_confidence REAL,
                warnings TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY(claim_id) REFERENCES claims(claim_id)
            );

            CREATE TABLE IF NOT EXISTS claim_images (
                image_id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL,
                view_type TEXT,
                original_filename TEXT,
                stored_path TEXT NOT NULL,
                overlay_path TEXT,
                mime_type TEXT,
                sha256 TEXT,
                perceptual_hash TEXT,
                quality_json TEXT,
                analysis_json TEXT,
                validation_status TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(claim_id) REFERENCES claims(claim_id)
            );

            CREATE TABLE IF NOT EXISTS damage_assessments (
                assessment_id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL,
                image_id TEXT,
                damaged_part TEXT,
                damage_type TEXT,
                severity TEXT,
                confidence REAL,
                damage_area TEXT,
                explanation TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(claim_id) REFERENCES claims(claim_id),
                FOREIGN KEY(image_id) REFERENCES claim_images(image_id)
            );

            CREATE TABLE IF NOT EXISTS estimations (
                estimate_id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL,
                repair_cost REAL,
                replacement_cost REAL,
                labor_cost REAL,
                material_cost REAL,
                deductible REAL,
                estimated_settlement REAL,
                source TEXT,
                status TEXT,
                cost_breakdown TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(claim_id) REFERENCES claims(claim_id)
            );

            CREATE TABLE IF NOT EXISTS verification_checks (
                check_id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL,
                check_name TEXT NOT NULL,
                status TEXT NOT NULL,
                explanation TEXT NOT NULL,
                evidence TEXT,
                can_continue INTEGER DEFAULT 1,
                recommended_action TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(claim_id) REFERENCES claims(claim_id)
            );

            CREATE TABLE IF NOT EXISTS reviewer_notes (
                note_id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                decision TEXT NOT NULL,
                comments TEXT,
                request_more_evidence INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(claim_id) REFERENCES claims(claim_id)
            );

            CREATE TABLE IF NOT EXISTS pricing_items (
                pricing_id TEXT PRIMARY KEY,
                vehicle_make TEXT,
                vehicle_model TEXT,
                component TEXT NOT NULL,
                damage_type TEXT NOT NULL,
                severity TEXT,
                repair_cost REAL,
                replacement_cost REAL,
                labor_cost REAL,
                material_cost REAL,
                currency TEXT DEFAULT 'INR',
                source TEXT,
                valid_for_demo INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )


def execute(query: str, params: Tuple[Any, ...] = ()) -> None:
    with get_conn() as conn:
        conn.execute(query, params)


def fetch_one(query: str, params: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(query, params).fetchone()
        return row_to_dict(row)


def fetch_all(query: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return rows_to_dicts(rows)


def upsert_user(name: str, email: Optional[str], contact: Optional[str]) -> str:
    user_id = new_id("USR")
    execute(
        "INSERT INTO users(user_id, name, email, contact, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, name, email, contact, now_iso()),
    )
    return user_id


def create_vehicle(user_id: str, vehicle: Dict[str, Any]) -> str:
    vehicle_id = new_id("VEH")
    execute(
        """
        INSERT INTO vehicles(vehicle_id, user_id, registration_number, make, model, year, vehicle_value, colour, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            vehicle_id,
            user_id,
            vehicle.get("registration_number"),
            vehicle.get("make"),
            vehicle.get("model"),
            vehicle.get("year"),
            vehicle.get("vehicle_value"),
            vehicle.get("colour"),
            now_iso(),
        ),
    )
    return vehicle_id


def create_policy(vehicle_id: str, policy: Optional[Dict[str, Any]]) -> Optional[str]:
    if not policy:
        return None
    policy_id = new_id("POL")
    execute(
        """
        INSERT INTO policies(policy_id, vehicle_id, policy_number, policy_type, start_date, end_date, idv, deductible,
                             coverage, exclusions, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            policy_id,
            vehicle_id,
            policy.get("policy_number"),
            policy.get("policy_type"),
            policy.get("start_date"),
            policy.get("end_date"),
            policy.get("idv"),
            policy.get("deductible"),
            dumps(policy.get("coverage") or []),
            dumps(policy.get("exclusions") or []),
            now_iso(),
        ),
    )
    return policy_id


def create_claim(user: Dict[str, Any], vehicle: Dict[str, Any], accident: Dict[str, Any], policy: Optional[Dict[str, Any]], demo_mode: bool, manual_repair_estimate: Optional[float]) -> str:
    user_id = upsert_user(user.get("name") or "Vehicle Owner", user.get("email"), user.get("contact"))
    vehicle_id = create_vehicle(user_id, vehicle)
    policy_id = create_policy(vehicle_id, policy)
    claim_id = new_id("CLM")
    execute(
        """
        INSERT INTO claims(claim_id, user_id, vehicle_id, policy_id, accident_date, claim_date, accident_location,
                           accident_description, claim_status, eligibility, estimated_amount, manual_repair_estimate,
                           demo_mode, validation_json, policy_json, claim_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            claim_id,
            user_id,
            vehicle_id,
            policy_id,
            accident.get("accident_date"),
            accident.get("claim_date"),
            accident.get("accident_location"),
            accident.get("accident_description"),
            "DRAFT",
            "NEEDS_VERIFICATION",
            None,
            manual_repair_estimate,
            1 if demo_mode else 0,
            dumps({}),
            dumps({}),
            dumps({}),
            now_iso(),
        ),
    )
    return claim_id


def update_claim_status(claim_id: str, status: str, eligibility: Optional[str] = None, estimated_amount: Optional[float] = None, validation: Optional[Dict[str, Any]] = None, policy_analysis: Optional[Dict[str, Any]] = None, claim_json: Optional[Dict[str, Any]] = None) -> None:
    current = get_claim(claim_id)
    execute(
        """
        UPDATE claims SET claim_status=?, eligibility=COALESCE(?, eligibility), estimated_amount=COALESCE(?, estimated_amount),
                          validation_json=COALESCE(?, validation_json), policy_json=COALESCE(?, policy_json),
                          claim_json=COALESCE(?, claim_json), updated_at=?
        WHERE claim_id=?
        """,
        (
            status,
            eligibility,
            estimated_amount,
            dumps(validation) if validation is not None else None,
            dumps(policy_analysis) if policy_analysis is not None else None,
            dumps(claim_json) if claim_json is not None else None,
            now_iso(),
            claim_id,
        ),
    )


def get_claim(claim_id: str) -> Optional[Dict[str, Any]]:
    claim = fetch_one("SELECT * FROM claims WHERE claim_id=?", (claim_id,))
    if not claim:
        return None
    claim["user"] = fetch_one("SELECT * FROM users WHERE user_id=?", (claim["user_id"],))
    claim["vehicle"] = fetch_one("SELECT * FROM vehicles WHERE vehicle_id=?", (claim["vehicle_id"],))
    claim["policy"] = fetch_one("SELECT * FROM policies WHERE policy_id=?", (claim.get("policy_id"),)) if claim.get("policy_id") else None
    claim["images"] = fetch_all("SELECT * FROM claim_images WHERE claim_id=? ORDER BY created_at", (claim_id,))
    claim["documents"] = fetch_all("SELECT * FROM documents WHERE claim_id=? ORDER BY created_at", (claim_id,))
    claim["damage_assessments"] = fetch_all("SELECT * FROM damage_assessments WHERE claim_id=? ORDER BY created_at", (claim_id,))
    claim["estimation"] = fetch_one("SELECT * FROM estimations WHERE claim_id=? ORDER BY created_at DESC LIMIT 1", (claim_id,))
    claim["verification_checks"] = fetch_all("SELECT * FROM verification_checks WHERE claim_id=? ORDER BY created_at", (claim_id,))
    return claim


def list_claims() -> List[Dict[str, Any]]:
    claims = fetch_all("SELECT * FROM claims ORDER BY created_at DESC")
    for claim in claims:
        claim["vehicle"] = fetch_one("SELECT * FROM vehicles WHERE vehicle_id=?", (claim["vehicle_id"],))
        claim["estimation"] = fetch_one("SELECT * FROM estimations WHERE claim_id=? ORDER BY created_at DESC LIMIT 1", (claim["claim_id"],))
        damage = fetch_all("SELECT severity FROM damage_assessments WHERE claim_id=?", (claim["claim_id"],))
        claim["damage_severity"] = _overall_severity([d.get("severity") for d in damage])
    return claims


def _overall_severity(severities: List[Optional[str]]) -> str:
    order = {"UNKNOWN": 0, "Minor": 1, "Moderate": 2, "Severe": 3}
    max_s = "UNKNOWN"
    for sev in severities:
        if order.get(str(sev), 0) > order.get(max_s, 0):
            max_s = str(sev)
    return max_s


def insert_image(claim_id: str, view_type: str, original_filename: str, stored_path: str, mime_type: str, sha256: str, perceptual_hash: str, quality: Dict[str, Any], validation_status: str) -> str:
    image_id = new_id("IMG")
    execute(
        """
        INSERT INTO claim_images(image_id, claim_id, view_type, original_filename, stored_path, mime_type, sha256,
                                 perceptual_hash, quality_json, analysis_json, validation_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (image_id, claim_id, view_type, original_filename, stored_path, mime_type, sha256, perceptual_hash, dumps(quality), dumps({}), validation_status, now_iso()),
    )
    return image_id


def update_image_analysis(image_id: str, analysis: Dict[str, Any], overlay_path: Optional[str] = None, validation_status: Optional[str] = None) -> None:
    execute(
        "UPDATE claim_images SET analysis_json=?, overlay_path=COALESCE(?, overlay_path), validation_status=COALESCE(?, validation_status) WHERE image_id=?",
        (dumps(analysis), overlay_path, validation_status, image_id),
    )


def insert_document(claim_id: str, document_type: str, original_filename: str, stored_path: str, mime_type: str,
                    extracted_text: str, extracted_fields: Dict[str, Any], verification_status: str,
                    ocr_confidence: Optional[float], warnings: List[str]) -> str:
    document_id = new_id("DOC")
    execute(
        """
        INSERT INTO documents(document_id, claim_id, document_type, original_filename, stored_path, mime_type,
                              extracted_text, extracted_fields, verification_status, ocr_confidence, warnings, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (document_id, claim_id, document_type, original_filename, stored_path, mime_type, extracted_text, dumps(extracted_fields), verification_status, ocr_confidence, dumps(warnings), now_iso()),
    )
    return document_id


def update_document_fields(document_id: str, fields: Dict[str, Any], verification_status: str) -> None:
    execute(
        "UPDATE documents SET extracted_fields=?, verification_status=?, updated_at=? WHERE document_id=?",
        (dumps(fields), verification_status, now_iso(), document_id),
    )


def replace_damage_assessments(claim_id: str, assessments: List[Dict[str, Any]]) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM damage_assessments WHERE claim_id=?", (claim_id,))
        for assessment in assessments:
            conn.execute(
                """
                INSERT INTO damage_assessments(assessment_id, claim_id, image_id, damaged_part, damage_type, severity,
                                               confidence, damage_area, explanation, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("DAM"),
                    claim_id,
                    assessment.get("image_id"),
                    assessment.get("damaged_part"),
                    assessment.get("damage_type"),
                    assessment.get("severity"),
                    assessment.get("confidence"),
                    dumps(assessment.get("damage_area") or {}),
                    assessment.get("explanation"),
                    now_iso(),
                ),
            )


def replace_verification_checks(claim_id: str, checks: List[Dict[str, Any]]) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM verification_checks WHERE claim_id=?", (claim_id,))
        for check in checks:
            conn.execute(
                """
                INSERT INTO verification_checks(check_id, claim_id, check_name, status, explanation, evidence,
                                                can_continue, recommended_action, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("CHK"),
                    claim_id,
                    check.get("check_name"),
                    check.get("status"),
                    check.get("explanation"),
                    check.get("evidence"),
                    1 if check.get("can_continue", True) else 0,
                    check.get("recommended_action"),
                    now_iso(),
                ),
            )


def insert_estimation(claim_id: str, estimate: Dict[str, Any]) -> str:
    estimate_id = new_id("EST")
    execute(
        """
        INSERT INTO estimations(estimate_id, claim_id, repair_cost, replacement_cost, labor_cost, material_cost,
                                deductible, estimated_settlement, source, status, cost_breakdown, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            estimate_id,
            claim_id,
            estimate.get("repair_cost"),
            estimate.get("replacement_cost"),
            estimate.get("labor_cost"),
            estimate.get("material_cost"),
            estimate.get("deductible"),
            estimate.get("estimated_settlement"),
            estimate.get("source"),
            estimate.get("status"),
            dumps(estimate.get("cost_breakdown") or []),
            now_iso(),
        ),
    )
    return estimate_id


def insert_pricing_item(item: Dict[str, Any]) -> str:
    pricing_id = new_id("PRI")
    execute(
        """
        INSERT INTO pricing_items(pricing_id, vehicle_make, vehicle_model, component, damage_type, severity,
                                  repair_cost, replacement_cost, labor_cost, material_cost, currency, source,
                                  valid_for_demo, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pricing_id,
            item.get("vehicle_make"),
            item.get("vehicle_model"),
            item.get("component"),
            item.get("damage_type"),
            item.get("severity"),
            item.get("repair_cost"),
            item.get("replacement_cost"),
            item.get("labor_cost"),
            item.get("material_cost"),
            item.get("currency", "INR"),
            item.get("source"),
            1 if item.get("valid_for_demo") else 0,
            now_iso(),
        ),
    )
    return pricing_id


def list_pricing_items(demo_only: bool = False) -> List[Dict[str, Any]]:
    if demo_only:
        return fetch_all("SELECT * FROM pricing_items WHERE valid_for_demo=1 ORDER BY component")
    return fetch_all("SELECT * FROM pricing_items ORDER BY component")


def add_reviewer_note(claim_id: str, reviewer: str, decision: str, comments: Optional[str], request_more_evidence: bool) -> str:
    note_id = new_id("REV")
    execute(
        """
        INSERT INTO reviewer_notes(note_id, claim_id, reviewer, decision, comments, request_more_evidence, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (note_id, claim_id, reviewer, decision, comments, 1 if request_more_evidence else 0, now_iso()),
    )
    return note_id

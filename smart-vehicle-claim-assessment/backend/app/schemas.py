from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


DISCLAIMER = (
    "AI-assisted preliminary assessment only. Final claim eligibility, repair assessment, "
    "and settlement are subject to insurer verification, policy terms, documentation, "
    "inspection, and applicable regulations."
)


class UserIn(BaseModel):
    name: str = "Demo User"
    email: Optional[str] = None
    contact: Optional[str] = None


class VehicleIn(BaseModel):
    registration_number: str = Field(default="", description="Vehicle Registration Number")
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    vehicle_value: Optional[float] = None
    colour: Optional[str] = None

    @field_validator("registration_number", mode="before")
    @classmethod
    def normalize_registration(cls, value: str) -> str:
        return "" if value is None else str(value).upper().replace(" ", "").replace("-", "")


class AccidentIn(BaseModel):
    accident_date: Optional[str] = None
    claim_date: Optional[str] = None
    accident_location: Optional[str] = None
    accident_description: Optional[str] = None


class PolicyIn(BaseModel):
    policy_number: Optional[str] = None
    policy_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    idv: Optional[float] = None
    deductible: Optional[float] = None
    coverage: Optional[List[str]] = None
    exclusions: Optional[List[str]] = None


class ClaimCreate(BaseModel):
    user: UserIn = Field(default_factory=UserIn)
    vehicle: VehicleIn = Field(default_factory=VehicleIn)
    accident: AccidentIn = Field(default_factory=AccidentIn)
    policy: Optional[PolicyIn] = None
    demo_mode: bool = False
    manual_repair_estimate: Optional[float] = Field(default=None, ge=0)


class ClaimUpdate(BaseModel):
    vehicle: Optional[VehicleIn] = None
    accident: Optional[AccidentIn] = None
    policy: Optional[PolicyIn] = None
    manual_repair_estimate: Optional[float] = Field(default=None, ge=0)


class OCRCorrection(BaseModel):
    fields: Dict[str, Any]
    verification_status: str = "USER_CORRECTED"


class PricingItemIn(BaseModel):
    vehicle_make: str
    vehicle_model: str
    component: str
    damage_type: str
    severity: str
    repair_cost: Optional[float] = None
    replacement_cost: Optional[float] = None
    labor_cost: Optional[float] = None
    material_cost: Optional[float] = None
    currency: str = "INR"
    source: str = "admin_configured"
    valid_for_demo: bool = False


class ReviewDecision(BaseModel):
    reviewer: str
    decision: str
    comments: Optional[str] = None
    request_more_evidence: bool = False


class StandardResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    disclaimer: str = DISCLAIMER

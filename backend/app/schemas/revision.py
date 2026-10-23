from datetime import datetime
from typing import List, Optional, Literal
from decimal import Decimal
from pydantic import BaseModel, Field
from backend.app.schemas.quality import QualityTestResultItem


class RevisionCreate(BaseModel):
    accepted_value: Decimal = Field(..., description="Curated scientific measurement value")
    decision: Literal["accepted", "corrected", "rejected", "needs_review"] = Field(
        ..., description="Review outcome decision"
    )
    reason: str = Field(..., min_length=5, max_length=2000, description="Mandatory rationale (minimum 5 characters)")
    calibration_id: Optional[int] = Field(None, description="Optional calibration reference ID")


class RevisionResponse(BaseModel):
    revision_id: int
    observation_id: int
    revision_number: int
    accepted_value: Decimal
    decision: str
    reason: str
    reviewer_id: int
    calibration_id: Optional[int]
    created_at: datetime


class ObservationSummary(BaseModel):
    observation_id: int
    sensor_id: int
    event_time: datetime
    received_at: datetime
    parameter_code: str
    raw_value: Decimal
    unit: str
    source_system: str
    source_message_id: str
    latest_quality_flag: Optional[str] = None
    current_accepted_value: Optional[Decimal] = None
    current_decision: Optional[str] = None
    revision_count: int = 0


class ObservationDetailResponse(BaseModel):
    observation_id: int
    sensor_id: int
    event_time: datetime
    received_at: datetime
    parameter_code: str
    raw_value: Decimal
    unit: str
    source_system: str
    source_message_id: str
    payload_hash: Optional[str] = None
    current_accepted_value: Optional[Decimal] = None
    current_decision: Optional[str] = None
    latest_quality_flag: Optional[str] = None
    quality_test_count: int = 0
    revision_count: int = 0
    quality_results: List[QualityTestResultItem] = []
    revisions: List[RevisionResponse] = []

from datetime import datetime
from typing import List, Optional, Literal, Any
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class ObservationInput(BaseModel):
    sensor_id: int = Field(..., description="Target sensor identifier")
    event_time: datetime = Field(..., description="Timestamp when observation occurred (ISO 8601 UTC)")
    received_at: Optional[datetime] = Field(None, description="Timestamp when observation was received (ISO 8601 UTC)")
    parameter_code: Literal["temperature", "salinity", "ph", "dissolved_oxygen"] = Field(
        ..., description="Allowlisted ocean parameter"
    )
    raw_value: Decimal = Field(..., description="Unmodified sensor measurement value")
    unit: str = Field(..., min_length=1, max_length=32, description="Measurement unit (e.g. degC, PSU, pH, mg/L)")
    source_system: str = Field(..., min_length=1, max_length=64, description="Telemetry origin system")
    source_message_id: str = Field(..., min_length=1, max_length=128, description="Unique source system message identifier")
    payload_hash: Optional[str] = Field(None, max_length=64, description="Cryptographic integrity hash")

    @field_validator("event_time", "received_at")
    @classmethod
    def validate_timezone_aware(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None and v.tzinfo is None:
            raise ValueError("Timestamp must be timezone-aware (ISO 8601 with offset or UTC 'Z').")
        return v


class IngestionBatch(BaseModel):
    atomic: bool = Field(True, description="When true, any non-duplicate invalid record rolls back the entire batch")
    records: List[ObservationInput] = Field(..., min_length=1, max_length=5000, description="Batch records (1 to 5,000)")


class BatchRecordError(BaseModel):
    index: int
    source_message_id: str
    error: str


class IngestionBatchResponse(BaseModel):
    batch_id: str
    status: Literal["committed", "rejected", "partial"]
    received_count: int
    inserted_count: int
    duplicate_count: int
    rejected_count: int
    observation_ids: List[int]
    errors: List[BatchRecordError] = []

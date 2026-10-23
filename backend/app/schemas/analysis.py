from datetime import datetime
from typing import List, Optional, Literal, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field


class AnalysisFilters(BaseModel):
    sensor_ids: Optional[List[int]] = Field(None, description="Optional list of sensor IDs to filter by")
    parameter_code: str = Field(..., description="Target ocean parameter (e.g. temperature, salinity, ph, dissolved_oxygen)")
    from_time: Optional[datetime] = Field(None, description="Start time filter (ISO 8601 UTC)")
    to_time: Optional[datetime] = Field(None, description="End time filter (ISO 8601 UTC)")
    revision_policy: Literal["latest_accepted_at_run", "raw_only"] = Field(
        "latest_accepted_at_run",
        description="Policy for resolving observation values: latest accepted revision at execution time, or raw telemetry only"
    )


class AnalysisCreate(BaseModel):
    analysis_name: str = Field(..., min_length=2, max_length=255, description="Human-readable analysis title")
    metric: Literal["mean", "min", "max", "count", "median", "standard_deviation"] = Field(
        ..., description="Statistical aggregation metric"
    )
    filters: AnalysisFilters = Field(..., description="Dataset selection and revision policy filters")
    query_version: str = Field(..., min_length=1, max_length=64, description="Analysis calculation kernel version identifier")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Custom calculation parameters")
    save_input_manifest: bool = Field(True, description="Whether to freeze exact input observation and revision IDs")


class AnalysisResultItem(BaseModel):
    metric_name: str
    metric_value: Decimal
    unit: str


class AnalysisResponse(BaseModel):
    analysis_id: int
    analysis_name: str
    metric: str
    status: str
    created_at: datetime
    query_version: str
    input_count: int
    results: List[AnalysisResultItem]


class ManifestItem(BaseModel):
    observation_id: int
    revision_id: Optional[int] = None
    input_role: str = "primary"


class AnalysisDetailResponse(BaseModel):
    analysis_id: int
    analysis_name: str
    metric: str
    query_version: str
    filters: Dict[str, Any]
    parameters: Dict[str, Any]
    status: str
    creator_id: int
    created_at: datetime
    input_count: int
    results: List[AnalysisResultItem]
    manifest: List[ManifestItem] = []


class ReplayResponse(BaseModel):
    analysis_id: int
    replayed_at: datetime
    original_results: List[AnalysisResultItem]
    replayed_results: List[AnalysisResultItem]
    matches: bool
    input_manifest_verified: bool

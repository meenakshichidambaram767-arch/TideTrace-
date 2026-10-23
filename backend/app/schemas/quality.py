from datetime import datetime
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class QualityRuleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    parameter_code: Literal["temperature", "salinity", "ph", "dissolved_oxygen"]
    rule_type: Literal["range", "gap", "rate_of_change", "stuck_sensor", "duplicate"]
    thresholds: Dict[str, Any]
    rule_version: str = Field(..., min_length=1, max_length=32)
    is_active: bool = True


class QualityRuleResponse(BaseModel):
    rule_id: int
    name: str
    parameter_code: str
    rule_type: str
    thresholds: Dict[str, Any]
    rule_version: str
    is_active: bool
    created_at: datetime


class QualityTestRequest(BaseModel):
    rule_ids: Optional[List[int]] = Field(None, description="Specific rule IDs to evaluate; if None, runs all active rules for parameter")
    include_temporal_checks: bool = Field(True, description="Whether to execute temporal gap, rate of change, and stuck sensor checks")


class QualityTestResultItem(BaseModel):
    test_result_id: int
    rule_id: int
    rule_name: str
    rule_version: str
    flag: Literal["pass", "suspect", "fail"]
    details: Dict[str, Any]
    tested_at: datetime


class QualityTestResponse(BaseModel):
    observation_id: int
    overall_flag: Literal["pass", "suspect", "fail"]
    results: List[QualityTestResultItem]

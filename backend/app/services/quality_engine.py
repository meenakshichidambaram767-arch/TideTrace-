from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.telemetry import Observation
from backend.app.models.quality import QualityRule, QualityTestResult
from backend.app.schemas.quality import QualityTestResponse, QualityTestResultItem
from backend.app.core.errors import NotFoundException


def evaluate_observation_quality(
    db: Session,
    observation_id: int,
    rule_ids: Optional[List[int]] = None,
    include_temporal_checks: bool = True,
) -> QualityTestResponse:
    """
    Execute versioned quality tests against a specific observation.
    Maintains historical provenance: test outcomes store the exact rule_id and version.
    Never alters or deletes raw observations.
    """
    now = datetime.now(timezone.utc)

    # 1. Retrieve target observation
    obs = db.query(Observation).filter(Observation.observation_id == observation_id).first()
    if not obs:
        raise NotFoundException(
            message=f"Observation with ID {observation_id} not found.",
            code="OBSERVATION_NOT_FOUND",
            details={"observation_id": observation_id},
        )

    # 2. Select rules to evaluate
    query = db.query(QualityRule).filter(
        QualityRule.is_active == True,
        QualityRule.parameter_code == obs.parameter_code,
    )
    if rule_ids:
        query = query.filter(QualityRule.rule_id.in_(rule_ids))

    rules = query.all()

    # If temporal checks are disabled, filter out temporal rule types
    if not include_temporal_checks:
        rules = [r for r in rules if r.rule_type not in ("gap", "rate_of_change", "stuck_sensor")]

    test_results_to_insert: List[QualityTestResult] = []
    response_items: List[QualityTestResultItem] = []
    overall_flags: List[str] = []

    # 3. Pre-fetch temporal context if temporal checks exist
    has_temporal_rules = any(r.rule_type in ("gap", "rate_of_change", "stuck_sensor") for r in rules)
    prior_observations: List[Observation] = []
    if has_temporal_rules:
        prior_observations = (
            db.query(Observation)
            .filter(
                Observation.sensor_id == obs.sensor_id,
                Observation.parameter_code == obs.parameter_code,
                Observation.event_time < obs.event_time,
            )
            .order_by(desc(Observation.event_time))
            .limit(10)
            .all()
        )

    # 4. Evaluate each rule
    for rule in rules:
        flag, details = evaluate_single_rule(obs, rule, prior_observations, db)
        overall_flags.append(flag)

        result_record = QualityTestResult(
            observation_id=obs.observation_id,
            rule_id=rule.rule_id,
            flag=flag,
            details=details,
            tested_at=now,
        )
        db.add(result_record)
        test_results_to_insert.append(result_record)

    db.flush()

    for rec, rule in zip(test_results_to_insert, rules):
        response_items.append(
            QualityTestResultItem(
                test_result_id=rec.test_result_id,
                rule_id=rule.rule_id,
                rule_name=rule.name,
                rule_version=rule.rule_version,
                flag=rec.flag,
                details=rec.details,
                tested_at=rec.tested_at,
            )
        )

    # 5. Determine overall flag
    if "fail" in overall_flags:
        overall_flag = "fail"
    elif "suspect" in overall_flags:
        overall_flag = "suspect"
    else:
        overall_flag = "pass"

    db.commit()

    return QualityTestResponse(
        observation_id=obs.observation_id,
        overall_flag=overall_flag,
        results=response_items,
    )


def evaluate_single_rule(
    obs: Observation,
    rule: QualityRule,
    priors: List[Observation],
    db: Session,
) -> Tuple[str, Dict[str, Any]]:
    """Evaluate an individual rule against an observation and return (flag, details)."""
    thresholds = rule.thresholds
    val = float(obs.raw_value)

    # --- 1. Range Check ---
    if rule.rule_type == "range":
        min_val = float(thresholds.get("min_value", -1e9))
        max_val = float(thresholds.get("max_value", 1e9))
        if val < min_val:
            return "suspect", {
                "violation": "below_minimum",
                "observed_value": val,
                "min_value": min_val,
                "max_value": max_val,
            }
        elif val > max_val:
            return "suspect", {
                "violation": "above_maximum",
                "observed_value": val,
                "min_value": min_val,
                "max_value": max_val,
            }
        return "pass", {"observed_value": val, "min_value": min_val, "max_value": max_val}

    # --- 2. Gap Check ---
    elif rule.rule_type == "gap":
        if not priors:
            return "pass", {"status": "insufficient_history", "reason": "No previous observation available for gap evaluation."}
        prev_obs = priors[0]
        gap_seconds = (obs.event_time - prev_obs.event_time).total_seconds()
        max_gap_hours = float(thresholds.get("max_gap_hours", 2.0))
        max_gap_seconds = max_gap_hours * 3600.0

        if gap_seconds > max_gap_seconds:
            return "suspect", {
                "violation": "temporal_gap_exceeded",
                "gap_hours": round(gap_seconds / 3600.0, 2),
                "threshold_max_gap_hours": max_gap_hours,
                "previous_event_time": prev_obs.event_time.isoformat(),
            }
        return "pass", {
            "gap_hours": round(gap_seconds / 3600.0, 2),
            "threshold_max_gap_hours": max_gap_hours,
        }

    # --- 3. Rate of Change Check ---
    elif rule.rule_type == "rate_of_change":
        if not priors:
            return "pass", {"status": "insufficient_history", "reason": "No previous observation available for rate of change calculation."}
        prev_obs = priors[0]
        prev_val = float(prev_obs.raw_value)
        delta_val = abs(val - prev_val)
        delta_seconds = (obs.event_time - prev_obs.event_time).total_seconds()
        delta_hours = max(delta_seconds / 3600.0, 1.0 / 3600.0)  # Avoid div by 0

        max_delta_per_hour = float(thresholds.get("max_delta_per_hour", 2.5))
        rate_per_hour = round(delta_val / delta_hours, 4)

        if rate_per_hour > max_delta_per_hour:
            return "suspect", {
                "violation": "rate_of_change_exceeded",
                "rate_per_hour": rate_per_hour,
                "max_delta_per_hour": max_delta_per_hour,
                "previous_value": prev_val,
                "current_value": val,
            }
        return "pass", {
            "rate_per_hour": rate_per_hour,
            "max_delta_per_hour": max_delta_per_hour,
        }

    # --- 4. Stuck Sensor Check ---
    elif rule.rule_type == "stuck_sensor":
        required_identical = int(thresholds.get("identical_threshold_count", 5))
        if len(priors) < (required_identical - 1):
            return "pass", {
                "status": "insufficient_history",
                "available_samples": len(priors) + 1,
                "required_samples": required_identical,
            }

        # Check if current and previous (N-1) values are all identical
        recent_values = [val] + [float(p.raw_value) for p in priors[: required_identical - 1]]
        all_identical = all(v == recent_values[0] for v in recent_values)

        if all_identical:
            return "suspect", {
                "violation": "stuck_sensor_detected",
                "identical_count": len(recent_values),
                "stuck_value": val,
            }
        return "pass", {
            "evaluated_samples": len(recent_values),
            "distinct_values": len(set(recent_values)),
        }

    # --- 5. Duplicate Check ---
    elif rule.rule_type == "duplicate":
        duplicate_obs = (
            db.query(Observation.observation_id)
            .filter(
                Observation.sensor_id == obs.sensor_id,
                Observation.parameter_code == obs.parameter_code,
                Observation.event_time == obs.event_time,
                Observation.observation_id != obs.observation_id,
            )
            .all()
        )
        if duplicate_obs:
            return "suspect", {
                "violation": "duplicate_readings_detected",
                "duplicate_ids": [d[0] for d in duplicate_obs],
            }
        return "pass", {"duplicate_count": 0}

    return "pass", {}

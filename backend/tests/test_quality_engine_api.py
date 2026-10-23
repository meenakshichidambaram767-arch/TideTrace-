import pytest
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from backend.app.models.telemetry import Observation
from backend.app.models.quality import QualityRule, QualityTestResult
from backend.app.db.session import SessionLocal


def test_range_check_anomalous_and_normal(client, reviewer_headers):
    """Test range check on both out-of-range spike and normal readings."""
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        # 1. Anomalous reading: 52.0 degC (threshold max is 35.0)
        anom_obs = Observation(
            sensor_id=1,
            event_time=now,
            received_at=now,
            parameter_code="temperature",
            raw_value=Decimal("52.0000"),
            unit="degC",
            source_system="buoy-test",
            source_message_id=f"msg-qc-range-anom-{uuid.uuid4().hex[:8]}",
        )
        # 2. Normal reading: 25.4 degC
        norm_obs = Observation(
            sensor_id=1,
            event_time=now + timedelta(minutes=1),
            received_at=now + timedelta(minutes=1),
            parameter_code="temperature",
            raw_value=Decimal("25.4000"),
            unit="degC",
            source_system="buoy-test",
            source_message_id=f"msg-qc-range-norm-{uuid.uuid4().hex[:8]}",
        )
        db.add_all([anom_obs, norm_obs])
        db.commit()
        anom_id = anom_obs.observation_id
        norm_id = norm_obs.observation_id

    # Evaluate anomalous
    resp_anom = client.post(
        f"/api/v1/observations/{anom_id}/quality-tests",
        json={"include_temporal_checks": False},
        headers=reviewer_headers,
    )
    assert resp_anom.status_code == 200
    data_anom = resp_anom.json()
    assert data_anom["overall_flag"] == "suspect"
    range_res = [r for r in data_anom["results"] if "range" in r["rule_name"]][0]
    assert range_res["flag"] == "suspect"
    assert range_res["details"]["violation"] == "above_maximum"

    # Evaluate normal
    resp_norm = client.post(
        f"/api/v1/observations/{norm_id}/quality-tests",
        json={"include_temporal_checks": False},
        headers=reviewer_headers,
    )
    assert resp_norm.status_code == 200
    data_norm = resp_norm.json()
    assert data_norm["overall_flag"] == "pass"


def test_temporal_gap_check(client, reviewer_headers):
    """Test that a temporal gap exceeding max_gap_hours triggers a suspect flag."""
    t0 = datetime(2026, 7, 10, 0, 0, 0, tzinfo=timezone.utc)
    with SessionLocal() as db:
        obs1 = Observation(
            sensor_id=3,
            event_time=t0,
            received_at=t0,
            parameter_code="temperature",
            raw_value=Decimal("24.0000"),
            unit="degC",
            source_system="buoy-test",
            source_message_id=f"msg-gap-1-{uuid.uuid4().hex[:8]}",
        )
        obs2 = Observation(
            sensor_id=3,
            event_time=t0 + timedelta(hours=18),
            received_at=t0 + timedelta(hours=18),
            parameter_code="temperature",
            raw_value=Decimal("24.5000"),
            unit="degC",
            source_system="buoy-test",
            source_message_id=f"msg-gap-2-{uuid.uuid4().hex[:8]}",
        )
        db.add_all([obs1, obs2])
        db.commit()

        gap_rule = db.query(QualityRule).filter_by(rule_type="gap", parameter_code="temperature").first()
        if not gap_rule:
            gap_rule = QualityRule(
                name="temperature_gap_check",
                parameter_code="temperature",
                rule_type="gap",
                thresholds={"max_gap_hours": 2.0},
                rule_version="v1.0",
                is_active=True,
                created_at=t0,
            )
            db.add(gap_rule)
            db.commit()
        gap_rule_id = gap_rule.rule_id
        target_obs_id = obs2.observation_id

    resp = client.post(
        f"/api/v1/observations/{target_obs_id}/quality-tests",
        json={"rule_ids": [gap_rule_id], "include_temporal_checks": True},
        headers=reviewer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_flag"] == "suspect"
    gap_res = data["results"][0]
    assert gap_res["flag"] == "suspect"
    assert gap_res["details"]["violation"] == "temporal_gap_exceeded"
    assert gap_res["details"]["gap_hours"] >= 18.0


def test_rate_of_change_check(client, reviewer_headers):
    """Test rate-of-change check flags abrupt delta exceeding threshold."""
    t0 = datetime(2026, 7, 11, 0, 0, 0, tzinfo=timezone.utc)
    with SessionLocal() as db:
        obs1 = Observation(
            sensor_id=4,
            event_time=t0,
            received_at=t0,
            parameter_code="temperature",
            raw_value=Decimal("22.0000"),
            unit="degC",
            source_system="buoy-test",
            source_message_id=f"msg-roc-1-{uuid.uuid4().hex[:8]}",
        )
        obs2 = Observation(
            sensor_id=4,
            event_time=t0 + timedelta(minutes=30),
            received_at=t0 + timedelta(minutes=30),
            parameter_code="temperature",
            raw_value=Decimal("31.0000"),
            unit="degC",
            source_system="buoy-test",
            source_message_id=f"msg-roc-2-{uuid.uuid4().hex[:8]}",
        )
        db.add_all([obs1, obs2])
        db.commit()

        roc_rule = db.query(QualityRule).filter_by(name="temperature_rate_of_change").first()
        roc_rule_id = roc_rule.rule_id
        target_id = obs2.observation_id

    resp = client.post(
        f"/api/v1/observations/{target_id}/quality-tests",
        json={"rule_ids": [roc_rule_id], "include_temporal_checks": True},
        headers=reviewer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_flag"] == "suspect"
    roc_res = data["results"][0]
    assert roc_res["flag"] == "suspect"
    assert roc_res["details"]["violation"] == "rate_of_change_exceeded"


def test_stuck_sensor_check(client, reviewer_headers):
    """Test that N consecutive identical values trigger stuck-sensor detection."""
    t0 = datetime(2028, 7, 12, 0, 0, 0, tzinfo=timezone.utc)
    readings = []
    for i in range(5):
        readings.append(
            Observation(
                sensor_id=5,
                event_time=t0 + timedelta(minutes=30 * i),
                received_at=t0 + timedelta(minutes=30 * i),
                parameter_code="temperature",
                raw_value=Decimal("21.4500"),
                unit="degC",
                source_system="buoy-test",
                source_message_id=f"msg-stuck-{i}-{uuid.uuid4().hex[:8]}",
            )
        )
    with SessionLocal() as db:
        db.add_all(readings)
        db.commit()
        target_obs_id = readings[-1].observation_id
        stuck_rule = db.query(QualityRule).filter_by(name="stuck_sensor_check").first()
        stuck_rule_id = stuck_rule.rule_id

    resp = client.post(
        f"/api/v1/observations/{target_obs_id}/quality-tests",
        json={"rule_ids": [stuck_rule_id], "include_temporal_checks": True},
        headers=reviewer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_flag"] == "suspect"
    stuck_res = data["results"][0]
    assert stuck_res["flag"] == "suspect"
    assert stuck_res["details"]["violation"] == "stuck_sensor_detected"


def test_duplicate_reading_detection(client, reviewer_headers):
    """Test duplicate check flags multiple readings for same sensor, parameter, and timestamp."""
    t0 = datetime(2026, 7, 13, 0, 0, 0, tzinfo=timezone.utc)
    with SessionLocal() as db:
        obs1 = Observation(
            sensor_id=1,
            event_time=t0,
            received_at=t0,
            parameter_code="salinity",
            raw_value=Decimal("34.5000"),
            unit="PSU",
            source_system="buoy-a",
            source_message_id=f"msg-dupcheck-1-{uuid.uuid4().hex[:8]}",
        )
        obs2 = Observation(
            sensor_id=1,
            event_time=t0,
            received_at=t0,
            parameter_code="salinity",
            raw_value=Decimal("34.6000"),
            unit="PSU",
            source_system="buoy-b",
            source_message_id=f"msg-dupcheck-2-{uuid.uuid4().hex[:8]}",
        )
        db.add_all([obs1, obs2])
        db.commit()

        dup_rule = db.query(QualityRule).filter_by(rule_type="duplicate", parameter_code="salinity").first()
        if not dup_rule:
            dup_rule = QualityRule(
                name="salinity_duplicate_check",
                parameter_code="salinity",
                rule_type="duplicate",
                thresholds={},
                rule_version="v1.0",
                is_active=True,
                created_at=t0,
            )
            db.add(dup_rule)
            db.commit()
        dup_rule_id = dup_rule.rule_id
        target_id = obs2.observation_id

    resp = client.post(
        f"/api/v1/observations/{target_id}/quality-tests",
        json={"rule_ids": [dup_rule_id], "include_temporal_checks": False},
        headers=reviewer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_flag"] == "suspect"
    dup_res = data["results"][0]
    assert dup_res["details"]["violation"] == "duplicate_readings_detected"


def test_quality_results_retain_exact_rule_version(client, reviewer_headers):
    """Test that stored test results explicitly preserve the exact rule version used."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        obs = Observation(
            sensor_id=1,
            event_time=now,
            received_at=now,
            parameter_code="ph",
            raw_value=Decimal("8.2000"),
            unit="pH",
            source_system="buoy-test",
            source_message_id=f"msg-versioned-{uuid.uuid4().hex[:8]}",
        )
        db.add(obs)
        db.commit()
        ph_rule = db.query(QualityRule).filter_by(name="ph_marine_range").first()
        ph_rule_id = ph_rule.rule_id
        obs_id = obs.observation_id

    resp = client.post(
        f"/api/v1/observations/{obs_id}/quality-tests",
        json={"rule_ids": [ph_rule_id]},
        headers=reviewer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    result_item = data["results"][0]
    assert result_item["rule_name"] == "ph_marine_range"
    assert result_item["rule_version"] == "v1.0"


def test_suspicious_reading_remains_intact_in_raw_observation(client, reviewer_headers):
    """Test that flagging a reading as suspect NEVER mutates or deletes the raw observation record."""
    now = datetime.now(timezone.utc)
    anomalous_val = Decimal("68.4000")
    with SessionLocal() as db:
        obs = Observation(
            sensor_id=1,
            event_time=now,
            received_at=now,
            parameter_code="temperature",
            raw_value=anomalous_val,
            unit="degC",
            source_system="buoy-test",
            source_message_id=f"msg-immutable-raw-{uuid.uuid4().hex[:8]}",
        )
        db.add(obs)
        db.commit()
        obs_id = obs.observation_id

    # Run tests
    resp = client.post(
        f"/api/v1/observations/{obs_id}/quality-tests",
        headers=reviewer_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["overall_flag"] == "suspect"

    with SessionLocal() as db:
        fresh_obs = db.query(Observation).filter_by(observation_id=obs_id).one()
        assert fresh_obs.raw_value == anomalous_val
        assert fresh_obs.parameter_code == "temperature"
        assert fresh_obs.event_time == now

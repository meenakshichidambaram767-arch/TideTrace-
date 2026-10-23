import pytest
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from backend.app.models.telemetry import Observation
from backend.app.models.revision import ObservationRevision
from backend.app.models.analysis import AnalysisRun, AnalysisInput, AnalysisResult
from backend.app.db.session import SessionLocal


def test_analysis_creation_and_retrieval(client, researcher_headers):
    """Test creating an analysis and retrieving its detail with frozen manifest."""
    t_start = datetime(2060, 1, 1, 0, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=int(uuid.uuid4().hex[:7], 16))
    t_end = t_start + timedelta(hours=2)

    with SessionLocal() as db:
        obs1 = Observation(
            sensor_id=1,
            event_time=t_start + timedelta(minutes=10),
            received_at=t_start + timedelta(minutes=10),
            parameter_code="temperature",
            raw_value=Decimal("24.0000"),
            unit="degC",
            source_system="buoy-test",
            source_message_id=f"msg-an-1-{uuid.uuid4().hex[:8]}",
        )
        obs2 = Observation(
            sensor_id=1,
            event_time=t_start + timedelta(minutes=20),
            received_at=t_start + timedelta(minutes=20),
            parameter_code="temperature",
            raw_value=Decimal("26.0000"),
            unit="degC",
            source_system="buoy-test",
            source_message_id=f"msg-an-2-{uuid.uuid4().hex[:8]}",
        )
        db.add_all([obs1, obs2])
        db.commit()

    payload = {
        "analysis_name": "Test Temperature Mean",
        "metric": "mean",
        "filters": {
            "sensor_ids": [1],
            "parameter_code": "temperature",
            "from_time": t_start.isoformat(),
            "to_time": t_end.isoformat(),
            "revision_policy": "latest_accepted_at_run",
        },
        "query_version": "mean-v1.0",
        "parameters": {"test_param": "alpha"},
        "save_input_manifest": True,
    }

    resp = client.post("/api/v1/analyses", json=payload, headers=researcher_headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "completed"
    assert data["metric"] == "mean"
    assert data["input_count"] == 2
    assert float(data["results"][0]["metric_value"]) == 25.0

    analysis_id = data["analysis_id"]

    # Retrieve detail
    detail_resp = client.get(f"/api/v1/analyses/{analysis_id}", headers=researcher_headers)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["analysis_id"] == analysis_id
    assert len(detail_data["manifest"]) == 2


def test_supported_metrics_calculation(client, researcher_headers):
    """Test calculation accuracy across all supported metrics: mean, min, max, count, median, standard_deviation."""
    t_base = datetime(2070, 1, 1, 0, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=int(uuid.uuid4().hex[:7], 16))
    values = [10.0, 20.0, 30.0, 40.0, 50.0]

    with SessionLocal() as db:
        obs_list = []
        for i, val in enumerate(values):
            obs_list.append(
                Observation(
                    sensor_id=2,
                    event_time=t_base + timedelta(minutes=10 * i),
                    received_at=t_base + timedelta(minutes=10 * i),
                    parameter_code="ph",
                    raw_value=Decimal(str(val)),
                    unit="pH",
                    source_system="buoy-test",
                    source_message_id=f"msg-metric-{i}-{uuid.uuid4().hex[:8]}",
                )
            )
        db.add_all(obs_list)
        db.commit()

    base_filters = {
        "sensor_ids": [2],
        "parameter_code": "ph",
        "from_time": t_base.isoformat(),
        "to_time": (t_base + timedelta(hours=2)).isoformat(),
        "revision_policy": "raw_only",
    }

    # Test each metric
    metric_expectations = {
        "mean": 30.0,
        "min": 10.0,
        "max": 50.0,
        "count": 5.0,
        "median": 30.0,
        "standard_deviation": 14.142136,  # pstdev of [10, 20, 30, 40, 50]
    }

    for metric_name, expected_val in metric_expectations.items():
        payload = {
            "analysis_name": f"Test {metric_name}",
            "metric": metric_name,
            "filters": base_filters,
            "query_version": "metrics-v1.0",
            "save_input_manifest": True,
        }
        res = client.post("/api/v1/analyses", json=payload, headers=researcher_headers)
        assert res.status_code == 201
        data = res.json()
        metric_val = float(data["results"][0]["metric_value"])
        assert abs(metric_val - expected_val) < 1e-4, f"Metric {metric_name}: expected {expected_val}, got {metric_val}"


def test_manifest_freezing_and_deterministic_replay_after_correction(client, researcher_headers, reviewer_headers):
    """
    CRITICAL PROVENANCE & DETERMINISTIC REPLAY TEST:
    Demonstrates that an analysis created before an observation correction can be
    replayed using its original frozen input manifest, with the original result
    preserved and the replay comparison verified honestly.
    """
    t_start = datetime(2080, 1, 1, 0, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=int(uuid.uuid4().hex[:7], 16))
    t_end = t_start + timedelta(hours=3)

    # 1. Ingest 3 raw observations: values 30.0, 32.0, 34.0 (Mean = 32.0)
    with SessionLocal() as db:
        obs1 = Observation(
            sensor_id=3,
            event_time=t_start + timedelta(minutes=10),
            received_at=t_start + timedelta(minutes=10),
            parameter_code="salinity",
            raw_value=Decimal("30.0000"),
            unit="PSU",
            source_system="buoy-test",
            source_message_id=f"msg-prov-1-{uuid.uuid4().hex[:8]}",
        )
        obs2 = Observation(
            sensor_id=3,
            event_time=t_start + timedelta(minutes=20),
            received_at=t_start + timedelta(minutes=20),
            parameter_code="salinity",
            raw_value=Decimal("32.0000"),  # Raw value = 32.0
            unit="PSU",
            source_system="buoy-test",
            source_message_id=f"msg-prov-2-{uuid.uuid4().hex[:8]}",
        )
        obs3 = Observation(
            sensor_id=3,
            event_time=t_start + timedelta(minutes=30),
            received_at=t_start + timedelta(minutes=30),
            parameter_code="salinity",
            raw_value=Decimal("34.0000"),
            unit="PSU",
            source_system="buoy-test",
            source_message_id=f"msg-prov-3-{uuid.uuid4().hex[:8]}",
        )
        db.add_all([obs1, obs2, obs3])
        db.commit()
        obs2_id = obs2.observation_id

    # 2. Run Analysis A BEFORE any correction (Mean = (30 + 32 + 34) / 3 = 32.0)
    payload_a = {
        "analysis_name": "Salinity Analysis Prior to Correction",
        "metric": "mean",
        "filters": {
            "sensor_ids": [3],
            "parameter_code": "salinity",
            "from_time": t_start.isoformat(),
            "to_time": t_end.isoformat(),
            "revision_policy": "latest_accepted_at_run",
        },
        "query_version": "salinity-mean-v1.0",
        "save_input_manifest": True,
    }

    resp_a = client.post("/api/v1/analyses", json=payload_a, headers=researcher_headers)
    assert resp_a.status_code == 201
    analysis_a_data = resp_a.json()
    analysis_a_id = analysis_a_data["analysis_id"]
    assert float(analysis_a_data["results"][0]["metric_value"]) == 32.0

    # Inspect Analysis A manifest: observation 2 was stored with revision_id = None (raw)
    detail_a = client.get(f"/api/v1/analyses/{analysis_a_id}", headers=researcher_headers).json()
    manifest_obs2 = [m for m in detail_a["manifest"] if m["observation_id"] == obs2_id][0]
    assert manifest_obs2["revision_id"] is None
    assert manifest_obs2["input_role"] == "raw"

    # 3. An oceanographer performs a correction on Observation 2!
    # Corrects value from 32.0 to 38.0!
    rev_payload = {
        "accepted_value": 38.0000,
        "decision": "corrected",
        "reason": "Calibration offset applied following post-cruise lab inspection.",
    }
    rev_resp = client.post(
        f"/api/v1/observations/{obs2_id}/revisions",
        json=rev_payload,
        headers={**reviewer_headers, "If-Match-Revision": "0"},
    )
    assert rev_resp.status_code == 201

    # 4. CRITICAL REPLAY TEST: Replay Analysis A!
    # Replay MUST use the frozen manifest (where obs2 had raw_value 32.0, NOT the new 38.0 revision!)
    replay_resp = client.post(f"/api/v1/analyses/{analysis_a_id}/replay", headers=researcher_headers)
    assert replay_resp.status_code == 200
    replay_data = replay_resp.json()

    assert replay_data["analysis_id"] == analysis_a_id
    assert replay_data["matches"] is True
    assert replay_data["input_manifest_verified"] is True
    assert float(replay_data["original_results"][0]["metric_value"]) == 32.0
    assert float(replay_data["replayed_results"][0]["metric_value"]) == 32.0

    # 5. Run Analysis B NOW (after the correction)
    # Analysis B incorporates the new revision: Mean = (30 + 38 + 34) / 3 = 34.0
    payload_b = {
        "analysis_name": "Salinity Analysis After Correction",
        "metric": "mean",
        "filters": {
            "sensor_ids": [3],
            "parameter_code": "salinity",
            "from_time": t_start.isoformat(),
            "to_time": t_end.isoformat(),
            "revision_policy": "latest_accepted_at_run",
        },
        "query_version": "salinity-mean-v1.0",
        "save_input_manifest": True,
    }
    resp_b = client.post("/api/v1/analyses", json=payload_b, headers=researcher_headers)
    assert resp_b.status_code == 201
    analysis_b_data = resp_b.json()
    analysis_b_id = analysis_b_data["analysis_id"]
    assert float(analysis_b_data["results"][0]["metric_value"]) == 34.0

    # Replay Analysis B -> Replays to 34.0
    replay_b_resp = client.post(f"/api/v1/analyses/{analysis_b_id}/replay", headers=researcher_headers)
    assert replay_b_resp.status_code == 200
    assert float(replay_b_resp.json()["replayed_results"][0]["metric_value"]) == 34.0

    # And replaying Analysis A STILL reproduces 32.0!
    replay_a_again = client.post(f"/api/v1/analyses/{analysis_a_id}/replay", headers=researcher_headers)
    assert float(replay_a_again.json()["replayed_results"][0]["metric_value"]) == 32.0


def test_unsupported_replay_calculation_version_rejection(client, researcher_headers):
    """Test that requesting replay with an unsupported or deprecated calculation version returns HTTP 422."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        run = AnalysisRun(
            analysis_name="Legacy Analysis",
            metric="mean",
            query_version="deprecated",  # Explicitly unsupported version
            filters={"parameter_code": "temperature"},
            parameters={},
            status="completed",
            creator_id=1,
            created_at=now,
        )
        db.add(run)
        db.commit()
        run_id = run.analysis_id

    resp = client.post(f"/api/v1/analyses/{run_id}/replay", headers=researcher_headers)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "REPLAY_VERSION_UNSUPPORTED"


def test_analyses_pagination(client, researcher_headers):
    """Test pagination on GET /analyses."""
    resp = client.get("/api/v1/analyses?page=1&page_size=2", headers=researcher_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "page" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["page_size"] == 2

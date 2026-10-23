import pytest
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from backend.app.models.telemetry import Observation
from backend.app.models.revision import ObservationRevision
from backend.app.models.audit import AuditEvent
from backend.app.db.session import SessionLocal


def test_authorized_revision_success(client, reviewer_headers):
    """Test that an authorized reviewer can append a valid revision with optimistic concurrency."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        obs = Observation(
            sensor_id=1,
            event_time=now,
            received_at=now,
            parameter_code="temperature",
            raw_value=Decimal("28.5000"),
            unit="degC",
            source_system="buoy-test",
            source_message_id=f"msg-rev-ok-{uuid.uuid4().hex[:8]}",
        )
        db.add(obs)
        db.commit()
        obs_id = obs.observation_id

    payload = {
        "accepted_value": 27.9000,
        "decision": "corrected",
        "reason": "Calibration thermistor offset applied based on monthly bench test.",
        "calibration_id": None,
    }

    headers = {**reviewer_headers, "If-Match-Revision": "0"}
    response = client.post(
        f"/api/v1/observations/{obs_id}/revisions",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["revision_number"] == 1
    assert data["decision"] == "corrected"
    assert float(data["accepted_value"]) == 27.9
    assert data["observation_id"] == obs_id


def test_unauthorized_revision_rejection(client, researcher_headers):
    """Test that a user with role 'researcher' cannot append a revision (HTTP 403 Forbidden)."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        obs = Observation(
            sensor_id=1,
            event_time=now,
            received_at=now,
            parameter_code="temperature",
            raw_value=Decimal("28.5000"),
            unit="degC",
            source_system="buoy-test",
            source_message_id=f"msg-rev-unauth-{uuid.uuid4().hex[:8]}",
        )
        db.add(obs)
        db.commit()
        obs_id = obs.observation_id

    payload = {
        "accepted_value": 27.0,
        "decision": "accepted",
        "reason": "Unauthorized researcher attempt.",
    }

    headers = {**researcher_headers, "If-Match-Revision": "0"}
    response = client.post(
        f"/api/v1/observations/{obs_id}/revisions",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN_INSUFFICIENT_ROLE"


def test_stale_revision_precondition_conflict(client, reviewer_headers):
    """Test that passing a stale If-Match-Revision returns HTTP 409 Conflict."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        obs = Observation(
            sensor_id=1,
            event_time=now,
            received_at=now,
            parameter_code="temperature",
            raw_value=Decimal("28.5000"),
            unit="degC",
            source_system="buoy-test",
            source_message_id=f"msg-rev-stale-{uuid.uuid4().hex[:8]}",
        )
        db.add(obs)
        db.commit()
        obs_id = obs.observation_id

    # 1. Create Revision 1
    resp1 = client.post(
        f"/api/v1/observations/{obs_id}/revisions",
        json={"accepted_value": 28.0, "decision": "needs_review", "reason": "First reviewer inspection."},
        headers={**reviewer_headers, "If-Match-Revision": "0"},
    )
    assert resp1.status_code == 201
    assert resp1.json()["revision_number"] == 1

    # 2. Attempt second revision using STALE precondition (If-Match-Revision: 0 instead of 1)
    resp2 = client.post(
        f"/api/v1/observations/{obs_id}/revisions",
        json={"accepted_value": 27.5, "decision": "corrected", "reason": "Concurrent conflicting review."},
        headers={**reviewer_headers, "If-Match-Revision": "0"},
    )
    assert resp2.status_code == 409
    error_data = resp2.json()["error"]
    assert error_data["code"] == "REVISION_CONFLICT"
    assert error_data["details"]["current_revision"] == 1
    assert error_data["details"]["expected_revision"] == 0


def test_revision_reason_min_length_validation(client, reviewer_headers):
    """Test that submitting a revision reason shorter than 5 characters returns HTTP 422."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        obs = Observation(
            sensor_id=1,
            event_time=now,
            received_at=now,
            parameter_code="temperature",
            raw_value=Decimal("28.5000"),
            unit="degC",
            source_system="buoy-test",
            source_message_id=f"msg-rev-short-{uuid.uuid4().hex[:8]}",
        )
        db.add(obs)
        db.commit()
        obs_id = obs.observation_id

    payload = {
        "accepted_value": 28.0,
        "decision": "accepted",
        "reason": "bad",
    }

    headers = {**reviewer_headers, "If-Match-Revision": "0"}
    response = client.post(
        f"/api/v1/observations/{obs_id}/revisions",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 422


def test_append_only_preservation_and_history(client, reviewer_headers):
    """Test that revisions are strictly append-only and history endpoint preserves all versions."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        obs = Observation(
            sensor_id=1,
            event_time=now,
            received_at=now,
            parameter_code="salinity",
            raw_value=Decimal("36.0000"),
            unit="PSU",
            source_system="buoy-test",
            source_message_id=f"msg-rev-history-{uuid.uuid4().hex[:8]}",
        )
        db.add(obs)
        db.commit()
        obs_id = obs.observation_id

    # Append Revision 1
    client.post(
        f"/api/v1/observations/{obs_id}/revisions",
        json={"accepted_value": 35.8, "decision": "needs_review", "reason": "Suspected biofouling drift."},
        headers={**reviewer_headers, "If-Match-Revision": "0"},
    )

    # Append Revision 2
    client.post(
        f"/api/v1/observations/{obs_id}/revisions",
        json={"accepted_value": 35.2, "decision": "corrected", "reason": "Cleaned sonde calibration offset applied."},
        headers={**reviewer_headers, "If-Match-Revision": "1"},
    )

    # Query revision history
    history_resp = client.get(
        f"/api/v1/observations/{obs_id}/revisions",
        headers=reviewer_headers,
    )
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) == 2
    assert history[0]["revision_number"] == 1
    assert history[0]["decision"] == "needs_review"
    assert history[1]["revision_number"] == 2
    assert history[1]["decision"] == "corrected"


def test_revision_audit_event_logged(client, reviewer_headers):
    """Test that appending a revision records an audit event in PostgreSQL."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        obs = Observation(
            sensor_id=1,
            event_time=now,
            received_at=now,
            parameter_code="temperature",
            raw_value=Decimal("25.0000"),
            unit="degC",
            source_system="buoy-test",
            source_message_id=f"msg-rev-audit-{uuid.uuid4().hex[:8]}",
        )
        db.add(obs)
        db.commit()
        obs_id = obs.observation_id

    client.post(
        f"/api/v1/observations/{obs_id}/revisions",
        json={"accepted_value": 25.2, "decision": "corrected", "reason": "Thermistor calibration offset."},
        headers={**reviewer_headers, "If-Match-Revision": "0"},
    )

    with SessionLocal() as db:
        audit = (
            db.query(AuditEvent)
            .filter_by(entity_type="observation", entity_id=str(obs_id), action="append_revision")
            .first()
        )
        assert audit is not None
        assert audit.details["decision"] == "corrected"

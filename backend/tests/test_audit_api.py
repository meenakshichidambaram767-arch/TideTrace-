import pytest
import uuid
from datetime import datetime, timezone, timedelta

from backend.app.models.audit import AuditEvent
from backend.app.db.session import SessionLocal


def test_audit_event_search_and_pagination(client, researcher_headers):
    """Test searching audit events with entity filters and pagination."""
    now = datetime.now(timezone.utc)
    unique_entity_id = f"test-audit-entity-{uuid.uuid4().hex[:8]}"

    with SessionLocal() as db:
        e1 = AuditEvent(
            entity_type="test_entity",
            entity_id=unique_entity_id,
            action="test_action_1",
            actor_id=1,
            event_time=now,
            reason="Integration test event 1",
            details={"step": 1},
        )
        e2 = AuditEvent(
            entity_type="test_entity",
            entity_id=unique_entity_id,
            action="test_action_2",
            actor_id=1,
            event_time=now + timedelta(seconds=1),
            reason="Integration test event 2",
            details={"step": 2},
        )
        db.add_all([e1, e2])
        db.commit()

    # Search by entity_id
    resp = client.get(
        f"/api/v1/audit-events?entity_type=test_entity&entity_id={unique_entity_id}&page=1&page_size=10",
        headers=researcher_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["entity_id"] == unique_entity_id


def test_analysis_and_replay_audit_logging(client, researcher_headers):
    """Test that creating and replaying an analysis both record audit trail events."""
    now = datetime.now(timezone.utc)
    t_start = now - timedelta(hours=1)

    payload = {
        "analysis_name": "Audit Logging Verification Analysis",
        "metric": "count",
        "filters": {
            "parameter_code": "temperature",
            "from_time": t_start.isoformat(),
            "to_time": now.isoformat(),
            "revision_policy": "raw_only",
        },
        "query_version": "count-v1.0",
        "save_input_manifest": True,
    }

    # 1. Create analysis
    create_resp = client.post("/api/v1/analyses", json=payload, headers=researcher_headers)
    assert create_resp.status_code == 201
    analysis_id = str(create_resp.json()["analysis_id"])

    # 2. Replay analysis
    replay_resp = client.post(f"/api/v1/analyses/{analysis_id}/replay", headers=researcher_headers)
    assert replay_resp.status_code == 200

    # 3. Verify audit events exist in /audit-events
    audit_resp = client.get(
        f"/api/v1/audit-events?entity_type=analysis_run&entity_id={analysis_id}",
        headers=researcher_headers,
    )
    assert audit_resp.status_code == 200
    events = audit_resp.json()["items"]
    actions = [e["action"] for e in events]
    assert "create_analysis" in actions
    assert "replay_analysis" in actions


def test_unauthenticated_audit_search_rejected(client):
    """Test that accessing /audit-events without Bearer token returns HTTP 401."""
    resp = client.get("/api/v1/audit-events")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "MISSING_AUTHORIZATION_HEADER"

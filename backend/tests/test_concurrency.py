import pytest
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.app.models.telemetry import Observation
from backend.app.models.revision import ObservationRevision
from backend.app.db.session import SessionLocal


def test_concurrent_revision_race_condition_prevention(client, reviewer_headers):
    """
    PostgreSQL Integration Concurrency Test:
    Simultaneously submit 5 concurrent revision attempts on the same observation
    with identical If-Match-Revision: 0.

    PostgreSQL locking semantics (SELECT ... FOR UPDATE) guarantee:
    1. Exactly ONE concurrent worker commits revision 1 with HTTP 201.
    2. The other concurrent workers receive HTTP 409 REVISION_CONFLICT.
    3. Exactly 1 revision row is persisted; no duplicate revision numbers or silent overwrites.
    """
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    obs = Observation(
        sensor_id=1,
        event_time=now,
        received_at=now,
        parameter_code="temperature",
        raw_value=Decimal("27.5000"),
        unit="degC",
        source_system="buoy-test",
        source_message_id=f"msg-conc-{uuid.uuid4().hex[:8]}",
    )
    db.add(obs)
    db.commit()
    obs_id = obs.observation_id
    db.close()

    def submit_revision(worker_id: int):
        payload = {
            "accepted_value": 27.0 + (worker_id * 0.1),
            "decision": "corrected",
            "reason": f"Concurrent review attempt by worker #{worker_id}.",
        }
        headers = {**reviewer_headers, "If-Match-Revision": "0"}
        resp = client.post(
            f"/api/v1/observations/{obs_id}/revisions",
            json=payload,
            headers=headers,
        )
        return resp.status_code, resp.json()

    # Launch 5 concurrent threads attempting revision
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(submit_revision, i) for i in range(5)]
        for fut in as_completed(futures):
            results.append(fut.result())

    status_codes = [r[0] for r in results]

    # Verification:
    # Exactly ONE thread gets 201 Created
    assert status_codes.count(201) == 1, f"Expected exactly one 201 Created, got {status_codes}"
    # All other 4 threads get 409 Conflict
    assert status_codes.count(409) == 4, f"Expected four 409 Conflicts, got {status_codes}"

    # Verify database state in PostgreSQL
    verify_db = SessionLocal()
    revisions = (
        verify_db.query(ObservationRevision)
        .filter(ObservationRevision.observation_id == obs_id)
        .all()
    )
    assert len(revisions) == 1
    assert revisions[0].revision_number == 1
    verify_db.close()

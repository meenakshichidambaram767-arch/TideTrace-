import pytest
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from backend.app.models.telemetry import Observation
from backend.app.models.audit import AuditEvent
from backend.app.db.session import SessionLocal


def test_successful_batch_ingestion(client, steward_headers):
    """Test standard valid batch ingestion with unique idempotency key."""
    idemp_key = f"test-ingest-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    payload = {
        "atomic": True,
        "records": [
            {
                "sensor_id": 1,
                "event_time": now.isoformat(),
                "received_at": (now + timedelta(seconds=15)).isoformat(),
                "parameter_code": "temperature",
                "raw_value": 26.8500,
                "unit": "degC",
                "source_system": "buoy-test-unit",
                "source_message_id": f"msg-{uuid.uuid4().hex[:10]}",
                "payload_hash": "sha256:test1",
            },
            {
                "sensor_id": 1,
                "event_time": (now + timedelta(minutes=15)).isoformat(),
                "received_at": (now + timedelta(minutes=15, seconds=20)).isoformat(),
                "parameter_code": "temperature",
                "raw_value": 26.9200,
                "unit": "degC",
                "source_system": "buoy-test-unit",
                "source_message_id": f"msg-{uuid.uuid4().hex[:10]}",
                "payload_hash": "sha256:test2",
            },
        ],
    }

    headers = {**steward_headers, "Idempotency-Key": idemp_key}
    response = client.post("/api/v1/ingestion/batches", json=payload, headers=headers)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["status"] == "committed"
    assert data["received_count"] == 2
    assert data["inserted_count"] == 2
    assert data["duplicate_count"] == 0
    assert len(data["observation_ids"]) == 2

    with SessionLocal() as db:
        for obs_id in data["observation_ids"]:
            obs = db.query(Observation).filter_by(observation_id=obs_id).first()
            assert obs is not None


def test_repeated_identical_ingestion_request(client, steward_headers):
    """Test that repeating an identical request with the same Idempotency-Key returns stored response without duplicating rows."""
    idemp_key = f"test-idemp-replay-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    msg_id = f"msg-replay-{uuid.uuid4().hex[:10]}"

    payload = {
        "atomic": True,
        "records": [
            {
                "sensor_id": 2,
                "event_time": now.isoformat(),
                "received_at": now.isoformat(),
                "parameter_code": "salinity",
                "raw_value": 35.1200,
                "unit": "PSU",
                "source_system": "buoy-test-unit",
                "source_message_id": msg_id,
            }
        ],
    }

    headers = {**steward_headers, "Idempotency-Key": idemp_key}

    # 1. First execution
    resp1 = client.post("/api/v1/ingestion/batches", json=payload, headers=headers)
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert data1["inserted_count"] == 1
    batch_id_1 = data1["batch_id"]

    # 2. Second execution (identical payload & key)
    resp2 = client.post("/api/v1/ingestion/batches", json=payload, headers=headers)
    assert resp2.status_code == 201
    data2 = resp2.json()

    # Must return cached result with same batch_id
    assert data2["batch_id"] == batch_id_1
    assert data2["observation_ids"] == data1["observation_ids"]

    with SessionLocal() as db:
        matching_obs = db.query(Observation).filter_by(source_message_id=msg_id).all()
        assert len(matching_obs) == 1


def test_reused_idempotency_key_with_different_payload_returns_409(client, steward_headers):
    """Test that reusing the same Idempotency-Key with a different payload returns HTTP 409 Conflict."""
    idemp_key = f"test-conflict-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    payload1 = {
        "atomic": True,
        "records": [
            {
                "sensor_id": 1,
                "event_time": now.isoformat(),
                "parameter_code": "temperature",
                "raw_value": 25.0,
                "unit": "degC",
                "source_system": "buoy-test",
                "source_message_id": f"msg-a-{uuid.uuid4().hex[:8]}",
            }
        ],
    }

    headers = {**steward_headers, "Idempotency-Key": idemp_key}
    resp1 = client.post("/api/v1/ingestion/batches", json=payload1, headers=headers)
    assert resp1.status_code == 201

    payload2 = {
        "atomic": True,
        "records": [
            {
                "sensor_id": 1,
                "event_time": now.isoformat(),
                "parameter_code": "temperature",
                "raw_value": 29.5,
                "unit": "degC",
                "source_system": "buoy-test",
                "source_message_id": f"msg-b-{uuid.uuid4().hex[:8]}",
            }
        ],
    }

    resp2 = client.post("/api/v1/ingestion/batches", json=payload2, headers=headers)
    assert resp2.status_code == 409
    error_data = resp2.json()
    assert error_data["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_record_level_duplicate_handling(client, steward_headers):
    """Test that duplicate records within a batch are skipped and counted while new records are inserted."""
    now = datetime.now(timezone.utc)
    existing_msg = f"msg-exist-{uuid.uuid4().hex[:8]}"

    # Ingest baseline record via API first
    init_payload = {
        "atomic": True,
        "records": [
            {
                "sensor_id": 1,
                "event_time": now.isoformat(),
                "parameter_code": "temperature",
                "raw_value": 25.0,
                "unit": "degC",
                "source_system": "buoy-test",
                "source_message_id": existing_msg,
            }
        ],
    }
    client.post(
        "/api/v1/ingestion/batches",
        json=init_payload,
        headers={**steward_headers, "Idempotency-Key": f"test-dup-base-{uuid.uuid4().hex[:8]}"},
    )

    # Now send batch containing duplicate record AND a brand new record
    new_msg = f"msg-new-{uuid.uuid4().hex[:8]}"
    payload = {
        "atomic": True,
        "records": [
            {
                "sensor_id": 1,
                "event_time": now.isoformat(),
                "parameter_code": "temperature",
                "raw_value": 25.0,
                "unit": "degC",
                "source_system": "buoy-test",
                "source_message_id": existing_msg,  # Duplicate!
            },
            {
                "sensor_id": 1,
                "event_time": (now + timedelta(minutes=5)).isoformat(),
                "parameter_code": "temperature",
                "raw_value": 25.1,
                "unit": "degC",
                "source_system": "buoy-test",
                "source_message_id": new_msg,  # New!
            },
        ],
    }

    idemp_key = f"test-dup-count-{uuid.uuid4().hex[:12]}"
    headers = {**steward_headers, "Idempotency-Key": idemp_key}
    response = client.post("/api/v1/ingestion/batches", json=payload, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["received_count"] == 2
    assert data["inserted_count"] == 1
    assert data["duplicate_count"] == 1


def test_atomic_batch_rollback_on_invalid_record(client, steward_headers):
    """Test that with atomic=True, an invalid record aborts and rolls back all newly inserted observations."""
    now = datetime.now(timezone.utc)
    msg_valid1 = f"msg-val1-{uuid.uuid4().hex[:8]}"
    msg_valid2 = f"msg-val2-{uuid.uuid4().hex[:8]}"
    msg_invalid = f"msg-inval-{uuid.uuid4().hex[:8]}"

    payload = {
        "atomic": True,
        "records": [
            {
                "sensor_id": 1,
                "event_time": now.isoformat(),
                "parameter_code": "temperature",
                "raw_value": 24.0,
                "unit": "degC",
                "source_system": "buoy-test",
                "source_message_id": msg_valid1,
            },
            {
                "sensor_id": 999999,  # INVALID SENSOR ID!
                "event_time": now.isoformat(),
                "parameter_code": "temperature",
                "raw_value": 24.0,
                "unit": "degC",
                "source_system": "buoy-test",
                "source_message_id": msg_invalid,
            },
            {
                "sensor_id": 1,
                "event_time": (now + timedelta(minutes=5)).isoformat(),
                "parameter_code": "temperature",
                "raw_value": 24.2,
                "unit": "degC",
                "source_system": "buoy-test",
                "source_message_id": msg_valid2,
            },
        ],
    }

    idemp_key = f"test-atomic-rollback-{uuid.uuid4().hex[:12]}"
    headers = {**steward_headers, "Idempotency-Key": idemp_key}
    response = client.post("/api/v1/ingestion/batches", json=payload, headers=headers)

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "ATOMIC_BATCH_VALIDATION_FAILED"

    # CRITICAL: Verify that NEITHER valid1 nor valid2 were committed in DB!
    with SessionLocal() as db:
        obs1 = db.query(Observation).filter_by(source_message_id=msg_valid1).first()
        obs2 = db.query(Observation).filter_by(source_message_id=msg_valid2).first()
        assert obs1 is None, "Valid record 1 should have been rolled back!"
        assert obs2 is None, "Valid record 2 should have been rolled back!"


def test_batch_size_limit_enforcement(client, steward_headers):
    """Test that attempting to ingest > 5,000 records returns HTTP 422."""
    now = datetime.now(timezone.utc)
    single_record = {
        "sensor_id": 1,
        "event_time": now.isoformat(),
        "parameter_code": "temperature",
        "raw_value": 25.0,
        "unit": "degC",
        "source_system": "buoy-test",
        "source_message_id": "dummy",
    }

    payload = {
        "atomic": True,
        "records": [single_record] * 5001,
    }

    idemp_key = f"test-size-limit-{uuid.uuid4().hex[:12]}"
    headers = {**steward_headers, "Idempotency-Key": idemp_key}
    response = client.post("/api/v1/ingestion/batches", json=payload, headers=headers)

    assert response.status_code == 422


def test_ingestion_audit_event_logged(client, steward_headers):
    """Test that successful batch ingestion records an audit event."""
    idemp_key = f"test-audit-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    payload = {
        "atomic": True,
        "records": [
            {
                "sensor_id": 1,
                "event_time": now.isoformat(),
                "parameter_code": "temperature",
                "raw_value": 27.0,
                "unit": "degC",
                "source_system": "buoy-test",
                "source_message_id": f"msg-audit-{uuid.uuid4().hex[:8]}",
            }
        ],
    }

    headers = {**steward_headers, "Idempotency-Key": idemp_key}
    response = client.post("/api/v1/ingestion/batches", json=payload, headers=headers)
    assert response.status_code == 201
    batch_id = response.json()["batch_id"]

    with SessionLocal() as db:
        audit = db.query(AuditEvent).filter_by(entity_type="ingestion_batch", entity_id=batch_id).first()
        assert audit is not None
        assert audit.action == "ingest_batch"

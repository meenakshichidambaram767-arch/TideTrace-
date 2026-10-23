# TideTrace: REST API Design Specification

**Document Version:** 1.0.0  
**Project:** TideTrace — Provenance-Aware Ocean Data Integrity and Anomaly Investigation System  
**Base Path:** `/api/v1` (Local dev: `http://localhost:8000/api/v1`)  
**Status:** Approved Architectural Baseline  

---

## 1. Conventions & Standards

### 1.1 Content Types & Encoding
- All endpoints accept and produce `application/json; charset=utf-8`.
- Timestamps sent or received must adhere strictly to ISO 8601 with explicit timezone offsets (e.g., `2026-10-22T08:00:00Z`). All timestamps are persisted and displayed in UTC.

### 1.2 Common Error Response Format
All error responses (4xx and 5xx) adhere to the standard error envelope:
```json
{
  "error": {
    "code": "REVISION_CONFLICT",
    "message": "The observation has a newer revision.",
    "details": {
      "expected_revision": 2,
      "current_revision": 3
    },
    "request_id": "req_01J9284XZ..."
  }
}
```

### 1.3 Standard Pagination Envelope
All listing endpoints return a consistent pagination envelope:
```json
{
  "items": [],
  "page": 1,
  "page_size": 50,
  "total": 128
}
```
Query parameters:
- `page`: Integer >= 1 (Default: 1)
- `page_size`: Integer between 1 and 100 (Default: 50)

### 1.4 Standard Request Headers
- `Authorization: Bearer <JWT_TOKEN>`: Mandatory on all endpoints except `GET /health` and `POST /auth/token`.
- `Idempotency-Key: <STRING>`: Mandatory for `POST /ingestion/batches` (min length 8, max 128).
- `If-Match-Revision: <INTEGER>`: Mandatory for `POST /observations/{id}/revisions` (optimistic lock token).
- `X-Request-Id: <STRING>`: Optional incoming client trace ID; if omitted, the server injects a UUIDv4.

---

## 2. Authentication Endpoint (Reconciliation GAP-01)

### `POST /auth/token`
Generates a JWT bearer token for role-based authentication.

- **Access:** Public
- **Request Body (`application/json`):**
```json
{
  "username": "reviewer_alice",
  "password": "CorrectHorseBatteryStaple!"
}
```
- **Responses:**
  - `200 OK`:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1Ni...",
    "token_type": "bearer",
    "user": {
      "user_id": 14,
      "username": "reviewer_alice",
      "full_name": "Alice Smith",
      "role": "reviewer"
    }
  }
  ```
  - `401 Unauthorized`: Invalid credentials.

---

## 3. Health Endpoint

### `GET /health`
Validates application and PostgreSQL connectivity.

- **Access:** Public
- **Response `200 OK`:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-10-23T04:00:00Z"
}
```

---

## 4. Station & Sensor Registry Endpoints (FR-01)

### `GET /stations`
List research stations.
- **Access:** Authenticated (Researcher, Reviewer, Steward, Admin)
- **Parameters:** `page`, `page_size`
- **Response `200 OK`:** Paginated stations.

### `POST /stations`
Register a new research station.
- **Access:** Data Steward, Administrator
- **Request Body (`StationCreate`):**
```json
{
  "station_name": "Bay Station A",
  "latitude": 10.25000,
  "longitude": 79.15000,
  "water_depth_m": 18.50
}
```
- **Response `201 Created`:**
```json
{
  "station_id": 12,
  "station_name": "Bay Station A",
  "latitude": 10.25000,
  "longitude": 79.15000,
  "water_depth_m": 18.50,
  "created_at": "2026-10-22T08:30:00Z"
}
```

### `GET /sensors`
List registered sensors.
- **Access:** Authenticated
- **Parameters:** `station_id` (int, opt), `sensor_type` (str, opt), `page`, `page_size`
- **Response `200 OK`:** Paginated sensors.

### `POST /sensors` (Reconciliation GAP-04)
Register a new sensor at a research station.
- **Access:** Data Steward, Administrator
- **Request Body (`SensorCreate`):**
```json
{
  "station_id": 12,
  "sensor_type": "CTD-Profiler",
  "serial_number": "CTD-99420-SN",
  "installed_at": "2026-10-01T00:00:00Z",
  "retired_at": null
}
```
- **Response `201 Created`:** Created sensor record with `sensor_id`.

---

## 5. Telemetry Ingestion Endpoints (FR-02)

### `POST /ingestion/batches`
Idempotent, atomic batch telemetry ingestion.

- **Access:** Data Steward, Ingestion Service, Administrator
- **Required Header:** `Idempotency-Key: ingest-demo-0001`
- **Request Body (`IngestionBatch`):**
```json
{
  "atomic": true,
  "records": [
    {
      "sensor_id": 7,
      "event_time": "2026-10-22T08:00:00Z",
      "received_at": "2026-10-22T08:03:00Z",
      "parameter_code": "temperature",
      "raw_value": 27.4000,
      "unit": "degC",
      "source_system": "buoy-sim-01",
      "source_message_id": "msg-000081",
      "payload_hash": "sha256:4a8b79c..."
    }
  ]
}
```
- **Responses:**
  - `201 Created`:
  ```json
  {
    "batch_id": "batch_20261022_0001",
    "status": "committed",
    "received_count": 1,
    "inserted_count": 1,
    "duplicate_count": 0,
    "rejected_count": 0,
    "observation_ids": [801],
    "errors": []
  }
  ```
  - `409 Conflict`: `IDEMPOTENCY_IN_PROGRESS`
  - `422 Unprocessable Entity`: Validation failure (if `atomic=true`, entire batch is rolled back).

---

## 6. Observation Search & Inspection (FR-03)

### `GET /observations`
Search observations with multi-dimensional filtering.
- **Access:** Authenticated
- **Parameters:**
  - `sensor_id` (int, opt)
  - `parameter_code` (str enum: `temperature`, `salinity`, `ph`, `dissolved_oxygen`, opt)
  - `from_time` (ISO 8601, opt)
  - `to_time` (ISO 8601, opt)
  - `quality_flag` (str enum: `pass`, `suspect`, `fail`, opt)
  - `page` (int, default 1)
  - `page_size` (int, default 50, max 100)
- **Response `200 OK`:** Paginated observation summary with latest flag and revision.

### `GET /observations/{observation_id}`
Retrieve complete detail of a single observation, including all quality test results and revision history.
- **Access:** Authenticated
- **Response `200 OK`:**
```json
{
  "observation_id": 801,
  "sensor_id": 7,
  "event_time": "2026-10-22T08:00:00Z",
  "received_at": "2026-10-22T08:03:00Z",
  "parameter_code": "temperature",
  "raw_value": 27.4,
  "unit": "degC",
  "source_system": "buoy-sim-01",
  "source_message_id": "msg-000081",
  "current_accepted_value": 26.9,
  "current_decision": "corrected",
  "latest_quality_flag": "suspect",
  "quality_test_count": 2,
  "revision_count": 1
}
```

---

## 7. Quality Control Rules & Testing (FR-04)

### `GET /quality-rules`
List quality rules and active versions.
- **Access:** Authenticated
- **Response `200 OK`:** Paginated list of rules.

### `POST /quality-rules` (Reconciliation GAP-05)
Create a new immutable rule version.
- **Access:** Data Steward, Administrator
- **Request Body (`QualityRuleCreate`):**
```json
{
  "name": "surface_temperature_range",
  "parameter_code": "temperature",
  "rule_type": "range",
  "thresholds": {
    "min_value": -2.0,
    "max_value": 35.0
  },
  "rule_version": "v1.2",
  "is_active": true
}
```
- **Response `201 Created`:** Rule metadata.

### `POST /observations/{observation_id}/quality-tests` (Reconciliation GAP-02, GAP-03)
Execute quality checks against an observation.
- **Access:** Reviewer, Data Steward, Administrator
- **Request Body:**
```json
{
  "rule_ids": [1, 2, 4],
  "include_temporal_checks": true
}
```
- **Response `200 OK`:**
```json
{
  "observation_id": 801,
  "overall_flag": "suspect",
  "results": [
    {
      "test_result_id": 9002,
      "rule_id": 4,
      "rule_name": "rate_of_change_v1",
      "flag": "suspect",
      "details": {
        "previous_value": 25.1,
        "delta": 2.3,
        "threshold": 1.5
      },
      "tested_at": "2026-10-22T08:04:00Z"
    }
  ]
}
```

---

## 8. Append-Only Measurement Revisions (FR-05)

### `GET /observations/{observation_id}/revisions`
Retrieve full audit history of revisions for an observation.
- **Access:** Authenticated
- **Response `200 OK`:** Array of revision entries ordered by `revision_number ASC`.

### `POST /observations/{observation_id}/revisions`
Append a reviewed correction or accepted decision.
- **Access:** Reviewer, Data Steward, Administrator
- **Required Header:** `If-Match-Revision: 2` (Must equal current revision number; use 0 if no revisions exist yet).
- **Request Body (`RevisionCreate`):**
```json
{
  "accepted_value": 26.9000,
  "decision": "corrected",
  "reason": "Calibration review documented a -0.5 degC sensor offset.",
  "calibration_id": 31
}
```
- **Responses:**
  - `201 Created`:
  ```json
  {
    "revision_id": 410,
    "observation_id": 801,
    "revision_number": 3,
    "accepted_value": 26.9000,
    "decision": "corrected",
    "reason": "Calibration review documented a -0.5 degC sensor offset.",
    "reviewer_id": 14,
    "calibration_id": 31,
    "created_at": "2026-10-22T09:15:00Z"
  }
  ```
  - `409 Conflict`: Stale revision precondition (`REVISION_CONFLICT`).
  - `422 Unprocessable Entity`: Reason shorter than 5 characters or validation failure.

---

## 9. Reproducible Analyses & Replay (FR-06, FR-07)

### `GET /analyses`
List executed analytical snapshots.
- **Access:** Authenticated
- **Response `200 OK`:** Paginated analysis list.

### `POST /analyses`
Execute a new reproducible analysis and record input manifest.
- **Access:** Researcher, Reviewer, Steward, Admin
- **Request Body (`AnalysisCreate`):**
```json
{
  "analysis_name": "Daily temperature mean - Bay Station A",
  "metric": "mean",
  "filters": {
    "sensor_ids": [7],
    "parameter_code": "temperature",
    "from_time": "2026-10-22T00:00:00Z",
    "to_time": "2026-10-23T00:00:00Z",
    "revision_policy": "latest_accepted_at_run"
  },
  "query_version": "daily-mean-v1",
  "parameters": {
    "group_by": "UTC_day"
  },
  "save_input_manifest": true
}
```
- **Response `201 Created`:**
```json
{
  "analysis_id": 77,
  "analysis_name": "Daily temperature mean - Bay Station A",
  "metric": "mean",
  "status": "completed",
  "created_at": "2026-10-22T09:20:00Z",
  "query_version": "daily-mean-v1",
  "input_count": 245,
  "results": [
    {
      "metric_name": "mean_temperature",
      "metric_value": 27.120000,
      "unit": "degC"
    }
  ]
}
```

### `GET /analyses/{analysis_id}`
Retrieve analysis results, metadata, and frozen input manifest.
- **Access:** Authenticated
- **Response `200 OK`:** Analysis metadata, results, and manifest items (`observation_id`, `revision_id`, `input_role`).

### `POST /analyses/{analysis_id}/replay` (Reconciliation GAP-08)
Recompute analysis strictly from the frozen input manifest.
- **Access:** Researcher, Reviewer, Steward, Admin
- **Response `200 OK`:**
```json
{
  "analysis_id": 77,
  "replayed_at": "2026-10-22T10:00:00Z",
  "original_results": [
    {
      "metric_name": "mean_temperature",
      "metric_value": 27.120000,
      "unit": "degC"
    }
  ],
  "replayed_results": [
    {
      "metric_name": "mean_temperature",
      "metric_value": 27.120000,
      "unit": "degC"
    }
  ],
  "matches": true,
  "input_manifest_verified": true
}
```

---

## 10. Audit Trail Search (FR-08)

### `GET /audit-events` (Reconciliation GAP-06, GAP-07)
Query immutable audit logs with multi-parameter filtering.
- **Access:** Data Steward, Administrator (Researchers permitted filtered views).
- **Parameters:**
  - `entity_type` (str, opt)
  - `entity_id` (str, opt)
  - `from_time` (ISO 8601, opt)
  - `to_time` (ISO 8601, opt)
  - `page` (int, default 1)
  - `page_size` (int, default 50)
- **Response `200 OK`:** Paginated audit log entries with action, actor ID, timestamp, and details.

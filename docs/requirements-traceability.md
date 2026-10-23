# TideTrace: Requirements Traceability Matrix (RTM)

**Document Version:** 1.0.0  
**Project:** TideTrace — Provenance-Aware Ocean Data Integrity and Anomaly Investigation System  
**Status:** Approved Architectural Baseline  

---

## 1. Executive Overview & Traceability Framework

The TideTrace system addresses critical data governance and scientific reproducibility challenges in oceanographic data management:
1. **Raw Observation Immutability:** Ingested sensor data is strictly append-only; quality flags or corrections never mutate raw telemetry.
2. **Versioned Quality Control:** Automated validation rules (range, gap, rate-of-change, stuck sensor, duplicate) are explicitly versioned, enabling historical auditability.
3. **Append-Only Measurement Revisions:** Scientific corrections require human-in-the-loop review with mandatory rationale and optimistic concurrency protection.
4. **Deterministic Analysis Manifests:** Analytical computations freeze exact observation and revision identifiers, guaranteeing deterministic replay even after future data updates.
5. **Database-First Integrity:** Business rules are enforced directly at the relational layer through composite keys, partial indexes, and transactional concurrency locks.

This document formally maps every requirement across the Product Requirements Document (PRD), API Contract, OpenAPI 3.1 specification, physical database schema, backend endpoints, UI components, and automated test suites.

---

## 2. Inconsistency Analysis & Smallest Consistent Resolutions

The following discrepancies were identified during cross-examination of `TideTrace_PRD.docx`, `TideTrace_API_Contract.docx`, and `tidetrace_openapi.json`. Each is resolved with the smallest consistent adjustment preserving full compliance.

| ID | Topic | PRD Statement | API Contract Statement | OpenAPI Spec (`tidetrace_openapi.json`) | Inconsistency / Gap | Smallest Consistent Resolution |
|---|---|---|---|---|---|---|
| **GAP-01** | **Authentication Endpoints** | §6 specifies JWT Bearer authentication, seeded roles (Researcher, Reviewer, Steward, Admin), and no committed secrets. | §1 & §8 specify Bearer JWT header across all endpoints except `/health`. Reviewer identity must be extracted from token. | `BearerAuth` security scheme defined; no `/auth/token` or `/auth/login` endpoint in `paths`. | OpenAPI omits the route to issue JWTs. | Add `POST /api/v1/auth/token` (OAuth2 password flow / JSON credentials) returning `access_token` and `token_type: "bearer"`. |
| **GAP-02** | **Quality Tests Request Payload** | §8.2 notes tests compare sensor/parameter in event-time order referencing rule versions. | §4.3 defines request body: `{ rule_ids: [1, 2, 4], include_temporal_checks: true }`. | `POST /observations/{id}/quality-tests` has empty requestBody definition. | OpenAPI missing request body schema. | Implement API Contract §4.3 schema: optional `rule_ids: list[int] = None` and `include_temporal_checks: bool = True`. |
| **GAP-03** | **Quality Test Response Payload** | §7 (FR-04) requires persisting versioned test results. | §4.3 defines `{ observation_id, overall_flag, results: [{ test_result_id, rule_id, rule_name, flag, details, tested_at }] }`. | Response schema is an unelaborated 200 description. | OpenAPI missing response model. | Standardize response model on API Contract §4.3 format with typed `flag` enum (`pass`, `suspect`, `fail`). |
| **GAP-04** | **Sensor Creation Request/Response** | §7 (FR-01) & §9 describe `sensor` entity with station, type, serial, installation dates. | §3 lists `POST /sensors` (Role: Data steward/admin, returns 201). | `POST /sensors` has no request body schema. | OpenAPI missing `SensorCreate` schema. | Define `SensorCreate` schema: `station_id: int`, `sensor_type: str`, `serial_number: str`, `installed_at: datetime`, `retired_at: Optional[datetime] = None`. |
| **GAP-05** | **Quality Rule Creation Schema** | §7 (FR-04) & §9 define `quality_rule` with name, parameter, rule_type, thresholds, version. | §3 lists `POST /quality-rules` (Role: Steward/admin, returns 201). | `POST /quality-rules` has no request body schema. | OpenAPI missing `QualityRuleCreate` schema. | Define `QualityRuleCreate` schema: `name: str`, `parameter_code: str`, `rule_type: str`, `thresholds: dict`, `rule_version: str`, `is_active: bool = True`. |
| **GAP-06** | **Pagination Parameters** | §7 (FR-03) requires paginated responses. | §5 defines standard envelope: `{ items, page, page_size, total }` with `page >= 1`, `page_size: 1..100`. | Only `/observations` defines `page` and `page_size`. `/sensors`, `/audit-events`, `/stations` lack params. | Parameter declaration omission in OpenAPI. | Apply query parameters `page: int = 1`, `page_size: int = 50` to all list endpoints (`/stations`, `/sensors`, `/observations`, `/quality-rules`, `/analyses`, `/audit-events`). |
| **GAP-07** | **Audit Entity ID Typing** | §8.1 uses string batch ID (`batch_20261022_0001`); §9 notes audit on entities. | §5 specifies entity_id filter for audit search. | `GET /audit-events` declares `entity_id` as `integer`. | Ingestion batch IDs and UUIDs are strings, causing type clash with `integer`. | In DB `audit_event`, define `entity_id VARCHAR(64)`. In API, support string `entity_id`, accepting both numeric strings and alphanumeric batch IDs. |
| **GAP-08** | **Replay Response Schema** | §7 (FR-07) requires equality report. | §4.6 specifies `{ analysis_id, replayed_at, original_results, replayed_results, matches, input_manifest_verified }`. | OpenAPI specifies 200 "Replay comparison" without schema. | OpenAPI schema unelaborated. | Adopt API Contract §4.6 schema in full. |
| **GAP-09** | **Reviewer Identity in Revisions** | §8.3 & §6 require reviewer identity for revisions. | §6 explicitly states: "Derive reviewer_id from the authenticated identity; do not trust client-supplied actor IDs." | `RevisionCreate` in OpenAPI has no `reviewer_id` in body. | Apparent contradiction with PRD §9 table schema. | No contradiction: client does NOT send `reviewer_id`; backend extracts reviewer identity from the verified JWT token claims. |

---

## 3. Functional Requirements Traceability Matrix (FR-01 to FR-10)

| Req ID | PRD Title & Acceptance Summary | Priority | API Endpoint | DB Feature / Tables | Backend Component | UI Screen | Verification Test |
|---|---|---|---|---|---|---|---|
| **FR-01** | **Station & Sensor Registry**<br>Create and list stations and sensors; enforce coordinate bounds and foreign keys. | Must | `GET /stations`<br>`POST /stations`<br>`GET /sensors`<br>`POST /sensors` | `research_station`, `sensor`, `sensor_deployment`<br>CHECK `latitude BETWEEN -90 AND 90`<br>CHECK `longitude BETWEEN -180 AND 180`<br>CHECK `water_depth_m >= 0`<br>FK `sensor.station_id` | `api/v1/endpoints/stations.py`<br>`api/v1/endpoints/sensors.py`<br>`services/registry_service.py` | Screen 1: Data Explorer (Station & Sensor metadata filters) | `tests/test_registry.py`<br>- `test_station_coordinate_bounds`<br>- `test_sensor_station_fk_enforcement` |
| **FR-02** | **Batch Ingestion**<br>Up to 5,000 records per request; idempotency key; duplicates counted; atomic rollback on invalid record when atomic=true. | Must | `POST /ingestion/batches`<br>Header: `Idempotency-Key` | `observation`, `idempotency_key`<br>UNIQUE `(source_system, source_message_id)`<br>Atomic transaction rollback<br>UTC timestamps | `api/v1/endpoints/ingestion.py`<br>`services/ingestion_service.py`<br>`db/transactions.py` | Screen 1: Data Explorer (Batch Ingestion modal) | `tests/test_ingestion.py`<br>- `test_idempotency_key_replay`<br>- `test_duplicate_source_message_skipped`<br>- `test_atomic_batch_rollback_on_failure`<br>- `test_batch_size_limit_5000` |
| **FR-03** | **Observation Search**<br>Filter by sensor, parameter, event-time range, and quality flag; paginated responses. | Must | `GET /observations`<br>`GET /observations/{id}` | `observation`, `quality_test_result`<br>Index `idx_observation_sensor_time`<br>Index `idx_observation_parameter_time` | `api/v1/endpoints/observations.py`<br>`services/observation_service.py` | Screen 1: Data Explorer (Filter table & detail drawer) | `tests/test_observations.py`<br>- `test_observation_time_range_filter`<br>- `test_observation_flag_filter`<br>- `test_pagination_window` |
| **FR-04** | **Quality Checks**<br>Persist versioned test results for range, gap, rate-of-change, stuck sensor, and duplicate checks. | Must | `POST /observations/{id}/quality-tests`<br>`GET /quality-rules`<br>`POST /quality-rules` | `quality_rule`, `quality_test_result`<br>FK `observation_id`, FK `rule_id`<br>Rule versioning immutability | `api/v1/endpoints/quality.py`<br>`services/quality_engine.py` | Screen 2: Quality Investigation (Flag summary & threshold rule manager) | `tests/test_quality_engine.py`<br>- `test_range_check`<br>- `test_rate_of_change_check`<br>- `test_stuck_sensor_check`<br>- `test_gap_check`<br>- `test_rule_version_immutability` |
| **FR-05** | **Revision Workflow**<br>Append revision with decision, reason (>= 5 chars), reviewer, calibration ID; optimistic concurrency via `If-Match-Revision`. | Must | `GET /observations/{id}/revisions`<br>`POST /observations/{id}/revisions`<br>Header: `If-Match-Revision` | `observation_revision`, `calibration`<br>UNIQUE `(observation_id, revision_number)`<br>Row lock: `SELECT ... FOR UPDATE`<br>CHECK `LENGTH(reason) >= 5` | `api/v1/endpoints/revisions.py`<br>`services/revision_service.py` | Screen 2: Quality Investigation (Revision timeline & revision submission modal) | `tests/test_revisions.py`<br>- `test_append_revision_success`<br>- `test_stale_revision_conflict_409`<br>- `test_concurrent_revision_race_condition`<br>- `test_min_reason_length_constraint` |
| **FR-06** | **Analysis Snapshots**<br>Store query version, parameters, results, and exact input revision manifest. | Must | `POST /analyses`<br>`GET /analyses`<br>`GET /analyses/{id}` | `analysis_run`, `analysis_input`, `analysis_result`<br>Composite PK `(analysis_id, observation_id)`<br>FK `(observation_id, revision_id)` | `api/v1/endpoints/analyses.py`<br>`services/analysis_service.py` | Screen 3: Reproducibility & Performance Lab (Analysis creator & manifest view) | `tests/test_analyses.py`<br>- `test_create_analysis_manifest_capture`<br>- `test_manifest_unaffected_by_subsequent_revisions` |
| **FR-07** | **Analysis Replay**<br>Replay from saved manifest and report whether output matches. | Must | `POST /analyses/{id}/replay` | `analysis_run`, `analysis_input`, `analysis_result`<br>Versioned analysis calculation kernel | `api/v1/endpoints/analyses.py`<br>`services/analysis_service.py` | Screen 3: Reproducibility & Performance Lab (Deterministic Replay comparison card) | `tests/test_replay.py`<br>- `test_deterministic_replay_match`<br>- `test_replay_uses_recorded_manifest_not_latest` |
| **FR-08** | **Audit Trail**<br>Search events by entity, actor, and timestamp; append-only storage. | Must | `GET /audit-events` | `audit_event`<br>Append-only permissions<br>Indexed by `entity_type`, `entity_id`, `event_time` | `api/v1/endpoints/audit.py`<br>`services/audit_service.py` | Global audit drawer / Screen 2 & 3 audit link | `tests/test_audit.py`<br>- `test_audit_event_logged_on_ingest`<br>- `test_audit_event_logged_on_revision`<br>- `test_audit_search_filters` |
| **FR-09** | **Query Benchmark**<br>Save `EXPLAIN (ANALYZE, BUFFERS)` evidence before and after index creation on 100,000+ rows. | Must | Benchmark CLI script / System runner | PostgreSQL core engine<br>`idx_observation_sensor_time`<br>`idx_observation_parameter_time` | `benchmarks/run_benchmarks.py`<br>`benchmarks/report_generator.py` | Screen 3: Reproducibility & Performance Lab (Benchmark comparison tab) | `tests/test_benchmarks.py`<br>- `test_explain_analyze_buffers_execution`<br>- `test_index_speedup_evidence` |
| **FR-10** | **Spatial Map**<br>PostGIS station map (Optional). | Could | `GET /stations` (extended GeoJSON) | PostGIS `geography(Point, 4326)` | Optional frontend Leaflet map | Screen 1: Optional Map View | Optional smoke test |

---

## 4. Non-Functional Requirements Traceability Matrix (NFR-01 to NFR-07)

| NFR ID | Category | Requirement Detail | Implementation Architecture | Verification Method |
|---|---|---|---|---|
| **NFR-01** | **Integrity** | Multi-step writes must be transactional; database constraints are the final barrier. | ACID transactions via SQLAlchemy 2.x session rollback; DB CHECK, UNIQUE, and composite FK constraints. | Automated rollback tests; intentional constraint violation unit tests. |
| **NFR-02** | **Auditability** | Raw observations, revisions, and audit logs are strictly append-only for normal application roles. | Relational design enforces no `UPDATE` / `DELETE` routes in API. PostgreSQL role permissions restrict DML to `INSERT`/`SELECT`. | SQL injection / unauthorized DML integration tests; DB privilege verification. |
| **NFR-03** | **Performance** | Benchmark queries on >= 100,000 synthetic observations; report actual `EXPLAIN (ANALYZE, BUFFERS)` evidence. | Seed script generating 100,000+ realistic oceanic rows; automated benchmark runner profiling buffer hits, disk reads, and execution times. | Automated benchmark script verifying plan cost and buffer hit improvements. |
| **NFR-04** | **Security** | Parameterized SQL, JWT role enforcement, least-privilege DB roles, secure secret configuration. | SQLAlchemy Core/ORM parameterized expressions; FastAPI `Depends(verify_role)` dependency; environment-based secrets. | Security test suite verifying role authorization matrix and SQL injection immunity. |
| **NFR-05** | **Reliability** | Timezone-aware API timestamps (ISO 8601); UTC storage; stable error codes and request IDs. | Pydantic datetime validation with UTC normalization; standard `Error` response envelope; UUIDv4 request ID middleware. | Request ID tracing tests; invalid timezone rejection tests. |
| **NFR-06** | **Maintainability** | Versioned Alembic migrations, complete OpenAPI 3.1 schema, seed script, modular service layout. | Alembic migration scripts; auto-generated and validated OpenAPI contract; modular layered architecture (`api`, `services`, `models`, `schemas`). | Alembic upgrade/downgrade migration tests; schema validation test. |
| **NFR-07** | **Usability** | User can complete ingest -> review -> correction -> analysis comparison entirely through UI without writing SQL. | React + Vite UI with unified navigation across 3 specialized screens (Data Explorer, Quality Review, Lab). | End-to-end user workflow test in browser/Playwright. |

---

## 5. Acceptance Criteria Traceability (PRD §12)

| # | Acceptance Test Statement | Implementing Module & Endpoint | Verified Test File & Function | Status |
|---|---|---|---|---|
| **AC-01** | Importing the same batch twice does not duplicate source messages. | `POST /ingestion/batches`<br>`services/ingestion_service.py` | `backend/tests/test_ingestion_api.py::test_repeated_identical_ingestion_request`<br>`backend/tests/test_ingestion_api.py::test_record_level_duplicate_handling` | **PASSED** |
| **AC-02** | A deliberately invalid atomic batch leaves no newly inserted observations. | `POST /ingestion/batches`<br>`services/ingestion_service.py` | `backend/tests/test_ingestion_api.py::test_atomic_batch_rollback_on_invalid_record` | **PASSED** |
| **AC-03** | A suspicious reading remains accessible in the raw observation table. | `POST /observations/{id}/quality-tests`<br>`services/quality_engine.py` | `backend/tests/test_quality_engine_api.py::test_suspicious_reading_remains_intact_in_raw_observation` | **PASSED** |
| **AC-04** | A correction creates a new revision and preserves earlier revisions. | `POST /observations/{id}/revisions`<br>`services/revision_service.py` | `backend/tests/test_revisions_api.py::test_append_only_preservation_and_history`<br>`backend/tests/test_db_constraints.py::test_raw_observation_immutability_and_revision_preservation` | **PASSED** |
| **AC-05** | Concurrent revision attempts cannot duplicate revision numbers; stale preconditions return HTTP 409. | `POST /observations/{id}/revisions`<br>`services/revision_service.py` | `backend/tests/test_concurrency.py::test_concurrent_revision_race_condition_prevention`<br>`backend/tests/test_revisions_api.py::test_stale_revision_precondition_conflict` | **PASSED** |
| **AC-06** | Analysis manifest stores exact revision IDs and remains unchanged after later corrections. | `POST /analyses`<br>`GET /analyses/{id}` | `backend/tests/test_analysis_replay_api.py::test_manifest_freezing_and_deterministic_replay_after_correction`<br>`backend/tests/test_db_constraints.py::test_analysis_manifest_integrity_and_immutability` | **PASSED** |
| **AC-07** | Replay uses the original manifest and reports equality accurately. | `POST /analyses/{id}/replay` | `backend/tests/test_analysis_replay_api.py::test_manifest_freezing_and_deterministic_replay_after_correction`<br>`backend/tests/test_analysis_replay_api.py::test_supported_metrics_calculation` | **PASSED** |
| **AC-08** | Before/after query plans and measured execution times are saved. | `scripts/benchmark_suite.py`<br>`docs/benchmarks.md` | `scripts/benchmark_suite.py` (EXPLAIN ANALYZE BUFFERS over 100k+ rows) | **PASSED** |
| **AC-09** | Unauthorized users cannot create revisions or mutate raw data. | `api/v1/dependencies/auth.py` | `backend/tests/test_revisions_api.py::test_unauthorized_revision_rejection`<br>`backend/tests/test_audit_api.py::test_unauthenticated_audit_search_rejected` | **PASSED** |

---

## 6. Non-Goals & Scope Guardrails (PRD §5.2)

To prevent scope creep and maintain strict architectural focus, the following boundaries are established:
- **NG-01:** TideTrace is **not** an operational ocean forecasting engine or hydrodynamic simulator.
- **NG-02:** Machine learning models are strictly out of scope for the MVP; statistical threshold and temporal rule engines satisfy all requirements.
- **NG-03:** Not a multi-tenant enterprise billing or organization management platform.
- **NG-04:** Synthetic data must be explicitly flagged with `source_system: "synthetic-generator"` and watermarked in UI visualizations to ensure it is never confused with empirical oceanographic datasets.
- **NG-05:** No arbitrary external plugins or unverified third-party analytics scripts.

# TideTrace: Technical Implementation Plan

**Document Version:** 1.0.0  
**Project:** TideTrace — Provenance-Aware Ocean Data Integrity and Anomaly Investigation System  
**Status:** Approved Architectural Baseline  

---

## 1. Planned Directory & File Structure

```
TideTrace/
├── .github/
│   └── workflows/
│       └── ci.yml
├── docs/
│   ├── requirements-traceability.md
│   ├── architecture.md
│   ├── database-design.md
│   ├── api-design.md
│   └── implementation-plan.md
├── backend/
│   ├── alembic/
│   │   ├── versions/
│   │   │   └── 001_initial_schema.py
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── alembic.ini
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── dependencies/
│   │   │       │   ├── auth.py
│   │   │       │   └── db.py
│   │   │       ├── endpoints/
│   │   │       │   ├── auth.py
│   │   │       │   ├── stations.py
│   │   │       │   ├── sensors.py
│   │   │       │   ├── ingestion.py
│   │   │       │   ├── observations.py
│   │   │       │   ├── quality.py
│   │   │       │   ├── revisions.py
│   │   │       │   ├── analyses.py
│   │   │       │   └── audit.py
│   │   │       └── router.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── errors.py
│   │   │   ├── middleware.py
│   │   │   └── security.py
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── transactions.py
│   │   ├── models/
│   │   │   ├── registry.py
│   │   │   ├── telemetry.py
│   │   │   ├── quality.py
│   │   │   ├── revision.py
│   │   │   ├── analysis.py
│   │   │   └── audit.py
│   │   ├── schemas/
│   │   │   ├── common.py
│   │   │   ├── registry.py
│   │   │   ├── ingestion.py
│   │   │   ├── observation.py
│   │   │   ├── quality.py
│   │   │   ├── revision.py
│   │   │   ├── analysis.py
│   │   │   └── audit.py
│   │   ├── services/
│   │   │   ├── registry_service.py
│   │   │   ├── ingestion_service.py
│   │   │   ├── observation_service.py
│   │   │   ├── quality_engine.py
│   │   │   ├── revision_service.py
│   │   │   ├── analysis_service.py
│   │   │   └── audit_service.py
│   │   └── main.py
│   ├── benchmarks/
│   │   ├── run_benchmarks.py
│   │   └── report_generator.py
│   ├── scripts/
│   │   ├── seed_data.py
│   │   └── generate_100k_dataset.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_registry.py
│   │   ├── test_ingestion.py
│   │   ├── test_observations.py
│   │   ├── test_quality_engine.py
│   │   ├── test_revisions.py
│   │   ├── test_analyses.py
│   │   ├── test_audit.py
│   │   ├── test_concurrency.py
│   │   └── test_acceptance.py
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── public/
│   │   └── favicon.svg
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   │   ├── Common/
│   │   │   │   ├── Header.jsx
│   │   │   │   ├── Navigation.jsx
│   │   │   │   ├── NotificationToast.jsx
│   │   │   │   └── Pagination.jsx
│   │   │   ├── DataExplorer/
│   │   │   │   ├── StationFilter.jsx
│   │   │   │   ├── ObservationGrid.jsx
│   │   │   │   ├── ObservationDrawer.jsx
│   │   │   │   └── IngestionModal.jsx
│   │   │   ├── QualityInvestigation/
│   │   │   │   ├── QualityRuleList.jsx
│   │   │   │   ├── FlagSummary.jsx
│   │   │   │   ├── RevisionHistory.jsx
│   │   │   │   └── SubmitRevisionModal.jsx
│   │   │   └── ReproducibilityLab/
│   │   │       ├── AnalysisBuilder.jsx
│   │   │       ├── ManifestViewer.jsx
│   │   │       ├── ReplayInspector.jsx
│   │   │       └── BenchmarkViewer.jsx
│   │   ├── context/
│   │   │   └── AuthContext.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── README.md
├── TideTrace_PRD.docx
├── TideTrace_API_Contract.docx
└── tidetrace_openapi.json
```

---

## 2. Phased Implementation Roadmap

### Phase 1: Relational Foundation, Migrations & Synthetic Data Engine (Week 1)
- **Database Initialization & Alembic:**
  - Establish PostgreSQL database connection pool in `backend/app/db/session.py`.
  - Implement full declarative SQLAlchemy 2.x models across registry, telemetry, curation, analysis, and audit domains.
  - Generate and verify Alembic migration `001_initial_schema.py` applying all check constraints, unique constraints, and foreign keys.
- **Station & Sensor Registry Service:**
  - Build Pydantic schemas for `StationCreate`, `SensorCreate`, and pagination filters.
  - Implement endpoints `GET /stations`, `POST /stations`, `GET /sensors`, `POST /sensors`.
- **Synthetic Data Generator (100,000+ Observations):**
  - Implement `scripts/seed_data.py` to seed research stations, sensors, initial users (Researcher, Reviewer, Steward, Admin), and calibration baselines.
  - Implement `scripts/generate_100k_dataset.py` with reproducible random seeds:
    - 5 sensors across 3–4 parameters (`temperature`, `salinity`, `ph`, `dissolved_oxygen`).
    - Injected test scenarios: duplicate messages, missing intervals, out-of-range spikes, stuck sensors, and late arrivals.
    - Explicitly labeled with `source_system: "synthetic-generator"`.

### Phase 2: Ingestion Pipeline, Quality Control Engine & Revision Concurrency (Week 2)
- **Atomic & Idempotent Ingestion Engine:**
  - Implement request-level idempotency locking using `idempotency_key` table.
  - Implement atomic batch ingestion (`POST /ingestion/batches`) handling up to 5,000 records.
  - Enforce rollback on invalid non-duplicate records when `atomic=true`.
  - Handle duplicate `(source_system, source_message_id)` entries cleanly via skip-and-count logic.
- **Versioned Quality Control Engine:**
  - Implement rule version manager (`GET /quality-rules`, `POST /quality-rules`).
  - Implement rule evaluator for Range, Gap, Rate-of-Change, Stuck Sensor, and Duplicate checks.
  - Implement `POST /observations/{id}/quality-tests` to persist versioned outcomes in `quality_test_result`.
- **Append-Only Revision Workflow & Concurrency Protection:**
  - Implement `GET /observations/{id}/revisions` and `POST /observations/{id}/revisions`.
  - Require and validate `If-Match-Revision` header.
  - Execute revision appending within a pessimistic transaction: `SELECT ... FOR UPDATE` on observation, ensuring sequential `revision_number` and returning HTTP 409 on stale preconditions.

### Phase 3: Analysis Manifests, Replay Engine, Audit Trail & Security (Week 3)
- **Reproducible Analysis Engine:**
  - Implement `POST /analyses` with metric calculators (`mean`, `min`, `max`, `count`, `median`, `standard_deviation`).
  - Freeze exact observation IDs and active revision IDs into `analysis_input`.
  - Store computed aggregations in `analysis_result`.
- **Deterministic Replay Engine:**
  - Implement `POST /analyses/{id}/replay`.
  - Retrieve exact input values from frozen manifest `analysis_input` (ignoring subsequent post-analysis revisions).
  - Recompute metrics and return verified match confirmation.
- **Audit Logging & Search:**
  - Implement unified `audit_event` recorder invoked across ingestion, revisions, rule changes, and analysis runs.
  - Implement `GET /audit-events` with entity, actor, and time filtering.
- **JWT Authentication & RBAC Filter:**
  - Implement `POST /auth/token` with secure password verification.
  - Enforce role-based access dependencies (`researcher`, `reviewer`, `steward`, `admin`) across all protected endpoints.

### Phase 4: Query Performance Lab, Three-Screen UI & Acceptance Suite (Week 4)
- **Query Performance Benchmarking Suite:**
  - Implement `benchmarks/run_benchmarks.py` executing `EXPLAIN (ANALYZE, BUFFERS)` on the 100k+ row observation table.
  - Capture plan cost, execution time, and shared hit/read buffer counts before and after `idx_observation_parameter_time`.
  - Persist benchmark outputs into `benchmarks/benchmark_results.json`.
- **Vite + React Modern Frontend:**
  - Design system with high-contrast, clean aesthetic (deep ocean dark mode, vibrant accents, glassmorphic cards, responsive tables).
  - **Screen 1: Data Explorer:** Observation tabular search, station/sensor filters, raw telemetry inspection drawer, and batch ingestion modal.
  - **Screen 2: Quality Investigation:** Rule version manager, quality flags overview, revision timeline, and interactive revision submission modal with `If-Match-Revision` feedback.
  - **Screen 3: Reproducibility & Performance Lab:** Analysis creator, frozen input manifest viewer, deterministic replay comparator, and query plan execution benchmark inspector.
- **End-to-End Acceptance Verification:**
  - Execute full suite `tests/test_acceptance.py` validating all 9 PRD acceptance tests.

---

## 3. Risk Assessment & Mitigations

| Risk | Impact | Mitigation Strategy |
|---|---|---|
| **Scope Creep into Ocean Modeling** | High | Strictly constrain scope to DBMS integrity, provenance, and statistical checks on 4 parameters. No complex physical simulation models. |
| **Silent Race Conditions on Revisions** | Critical | Enforce pessimistic `SELECT ... FOR UPDATE` locking on observation rows during revisions; enforce DB constraint `UNIQUE (observation_id, revision_number)`. |
| **Replay Drift After Logic Updates** | High | Store `query_version` with each analysis run. Reject replay or return explicit deprecation error if the requested analysis query kernel version is unsupported. |
| **Synthetic Telemetry Confused with Empirical Data** | Medium | Mandatory metadata tags (`source_system: "synthetic-generator"`) and prominent UI watermarks on all generated data. |
| **Buffer Cache Invalidation in Benchmarks** | Medium | Warm up cache consistently and report distinct cold/warm buffer statistics in `EXPLAIN (ANALYZE, BUFFERS)`. |

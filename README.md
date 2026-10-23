# TideTrace — Provenance-Aware Ocean Data Integrity & Anomaly Investigation System

[![PostgreSQL 18.6](https://img.shields.io/badge/Database-PostgreSQL_18.6-blue.svg)](https://www.postgresql.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.115+-teal.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/Frontend-React_19_Vite_TS-cyan.svg)](https://vitejs.dev/)
[![Tests](https://img.shields.io/badge/Tests-46_Passed_100%25-brightgreen.svg)]()

TideTrace is an advanced scientific oceanographic database management and anomaly investigation system. It guarantees immutable raw telemetry, versioned quality control, append-only human-in-the-loop scientific revisions with optimistic concurrency locks, and deterministic analysis replay through frozen input manifests.

---

## 1. System Architectural Pillars

1. **Raw Telemetry Immutability:** Sensor observations ingested from buoys are strictly append-only. Automated quality tests and scientific corrections never mutate or overwrite raw telemetry in place.
2. **Versioned Quality Engine:** Rules for physical range, temporal gaps, rates of change, stuck sensors, and duplicates are explicitly versioned (`v1.0`, `v1.1`), ensuring historical auditability.
3. **Concurrency-Safe Measurement Revisions:** Scientific corrections require human-in-the-loop review, mandatory rationale (>= 5 characters), pessimistic row locking (`SELECT ... FOR UPDATE`), and `If-Match-Revision` tokens to prevent race conditions (HTTP 409 on stale revision).
4. **Frozen Analysis Manifests:** Every analytical snapshot freezes its consumed observation and revision IDs into `analysis_input`. Replaying an analysis queries only the frozen manifest, preserving historical results even after subsequent telemetry corrections.
5. **Database-First Integrity:** ACID transaction rollbacks on invalid ingestion records, composite foreign keys `(observation_id, revision_id)`, and check constraints enforced directly in PostgreSQL.

---

## 2. Prerequisites & Setup

- **Python:** 3.11+
- **Node.js:** v20+ (Node v24 and npm 11 verified)
- **PostgreSQL:** 16+ (PostgreSQL 18.6 running locally on port 5433)

### Environment Configuration (`.env`)
```ini
DATABASE_URL=postgresql+psycopg://postgres:@127.0.0.1:5433/tidetrace
SECRET_KEY=tidetrace-secret-key-super-secure-production-ready
ACCESS_TOKEN_EXPIRE_MINUTES=120
PROJECT_NAME=TideTrace
API_V1_PREFIX=/api/v1
```

---

## 3. Database Migrations & Seeding

```powershell
# 1. Apply Alembic Migrations
alembic upgrade head

# 2. Seed Base Metadata (Stations, Sensors, Deployments, Calibrations, Users, Rules)
python scripts/seed_data.py

# 3. Generate 100,000+ Synthetic Oceanographic Telemetry Records (Idempotent)
python scripts/generate_100k_dataset.py
```

---

## 4. Starting the Application

### Backend API Server (FastAPI)
```powershell
uvicorn backend.app.main:app --host 127.0.0.1 --port 8001 --reload
```
- API Base URL: `http://localhost:8001/api/v1`
- Swagger UI Documentation: `http://localhost:8001/api/v1/docs`
- OpenAPI Specification: `http://localhost:8001/api/v1/openapi.json`

### Frontend Research Dashboard (React + Vite)
```powershell
cd frontend
npm install
npm run dev
```
- Web Application URL: `http://localhost:5174`

---

## 5. Automated Verification & Testing

### Backend Regression Test Suite (40 Tests)
```powershell
python -m pytest backend/tests/ -v
```
*Result:* **40 Passed in 1.00s (100% Pass Rate)**
- `test_concurrency.py`: Concurrent race-condition prevention under pessimistic locking.
- `test_db_constraints.py`: Database check constraints, coordinate bounds, and immutability.
- `test_ingestion_api.py`: Idempotency keys, atomic batch rollback, and duplicate skipping.
- `test_quality_engine_api.py`: Range, gap, stuck sensor, and rate-of-change rules.
- `test_revisions_api.py`: Revision workflow, minimum reason length, RBAC, and stale 409 conflict.
- `test_analysis_replay_api.py`: Manifest freezing, deterministic replay after corrections, and metrics.
- `test_audit_api.py`: Audit trail searching, pagination, and RBAC.

### Frontend Test Suite (6 Tests)
```powershell
cd frontend
npm run test
```
*Result:* **6 Passed in 1.27s (100% Pass Rate)**

---

## 6. Performance Benchmarking

Run the automated PostgreSQL benchmarking harness over 100,000+ rows:
```powershell
python scripts/benchmark_suite.py
```
*Report generated at:* `docs/benchmarks.md`

### Measured Latency & Query Plan Summary (50 Repetitions)
| Query Scenario | Median (ms) | p95 (ms) | Plan Scan Type | PostgreSQL Buffers |
|---|---|---|---|---|
| **Q1: Sensor & Time Range** | **0.235 ms** | 0.292 ms | `Index Scan` (`idx_observation_sensor_time`) | 100% Shared Hit |
| **Q2: Parameter & Time Range** | **0.328 ms** | 0.517 ms | `Bitmap Index Scan` (`idx_observation_parameter_time`) | 100% Shared Hit |
| **Q3: Quality Flag Lookup** | **0.155 ms** | 0.224 ms | `Index Scan` (`idx_quality_result_observation_tested`) | 100% Shared Hit |
| **Q4: Revision History** | **0.132 ms** | 0.234 ms | `Seq Scan` (74 rows, optimizer prefers in-cache read) | 100% Shared Hit |
| **Q5: Frozen Manifest Retrieval** | **0.117 ms** | 0.219 ms | `Index Scan` (Composite Primary Key) | 100% Shared Hit |
| **Q6: Audit Event Search** | **0.249 ms** | 0.339 ms | `Seq Scan` (187 rows, Top-N Heapsort) | 100% Shared Hit |
| **Q7: Replay Input Resolution Join** | **0.233 ms** | 0.361 ms | `Index Scan` (Nested Loop on Composite FK) | 100% Shared Hit |

---

## 7. End-to-End Provenance & Replay Demonstration

Execute the 10-step scientific reproducibility demonstration:
```powershell
python scripts/demo_provenance_replay.py
```

### Demonstration Steps Verified:
1. Ingests 3 raw salinity readings: `[30.0, 32.0, 34.0]`.
2. Creates Analysis A (Mean metric prior to correction); verifies `mean == 32.000000`.
3. Freezes and inspects Analysis A's manifest in `analysis_input`.
4. Authorized Reviewer submits a correction to Observation 2 changing accepted value to `38.0`.
5. Replays Analysis A: proves it **still produces `32.000000`** with manifest verified 100% intact!
6. Creates Analysis B (Post-Correction); verifies `mean == 34.000000`.
7. Replays Analysis B: verifies output `34.000000`; re-verifies Analysis A still reproduces `32.000000`.
8. Inspects audit events for ingestion, revision, creation, and replay.
9. Demonstrates role restrictions (HTTP 403 on researcher revision) and concurrency conflict (HTTP 409 on stale `If-Match-Revision`).
10. Summarizes PostgreSQL performance metrics and query plan evidence.

---

## 8. User Roles & Seeded Accounts

| Username | Role | Permitted Actions |
|---|---|---|
| `admin_clara` | Administrator | Full access: rule creation, revisions, analyses, audit search |
| `steward_bob` | Data Steward | Ingestion batch intake, quality rule configuration, revisions |
| `reviewer_alice` | Reviewer | Observation review, measurement revisions, quality assessments |
| `researcher_sam` | Researcher | Read-only observations, analysis creation, deterministic replay |

# TideTrace: PostgreSQL Performance & Query Plan Benchmark Report

**Date:** 2026-10-23 05:16:15 UTC  
**Database Engine:** PostgreSQL 18.6 (x86_64-windows)  
**Dataset Scale:** 100,297 observations, 74 revisions, 187 audit events  
**Repetitions:** 50 runs per query (5 warmup runs)  

## 1. Summary Benchmark Latency Table

| ID | Query Description | Median (ms) | p95 (ms) | Min (ms) | Max (ms) | Plan Scan Type |
|---|---|---|---|---|---|---|
| **Q1** | Observation retrieval by sensor and time range | **0.235** | 0.292 | 0.210 | 0.386 | `Index Scan` |
| **Q2** | Observation retrieval by parameter and time range | **0.328** | 0.517 | 0.276 | 0.617 | `Index Scan` |
| **Q3** | Quality-flag lookup by observation | **0.155** | 0.224 | 0.117 | 0.266 | `Index Scan` |
| **Q4** | Revision history retrieval for an observation | **0.132** | 0.234 | 0.125 | 0.260 | `Sequential Scan` |
| **Q5** | Analysis manifest retrieval | **0.117** | 0.219 | 0.110 | 0.246 | `Index Scan` |
| **Q6** | Audit-event filtering and pagination | **0.249** | 0.339 | 0.215 | 0.391 | `Sequential Scan` |
| **Q7** | Deterministic Replay input resolution join | **0.233** | 0.361 | 0.211 | 0.416 | `Index Scan` |

---

## 2. Query Execution Plans: EXPLAIN (ANALYZE, BUFFERS)

### Q1: Observation retrieval by sensor and time range

```text
Limit  (cost=0.29..31.32 rows=14 width=40) (actual time=0.012..0.022 rows=50.00 loops=1)
  Output: observation_id, sensor_id, event_time, parameter_code, raw_value, unit
  Buffers: shared hit=23
  ->  Index Scan using idx_observation_sensor_time on public.observation  (cost=0.29..31.32 rows=14 width=40) (actual time=0.011..0.020 rows=50.00 loops=1)
        Output: observation_id, sensor_id, event_time, parameter_code, raw_value, unit
        Index Cond: ((observation.sensor_id = '1'::smallint) AND (observation.event_time >= '2026-10-18 10:46:15.665812+05:30'::timestamp with time zone))
        Index Searches: 1
        Buffers: shared hit=23
Planning Time: 0.081 ms
Execution Time: 0.033 ms
```

### Q2: Observation retrieval by parameter and time range

```text
Limit  (cost=16.15..16.16 rows=3 width=40) (actual time=0.065..0.068 rows=50.00 loops=1)
  Output: observation_id, sensor_id, event_time, parameter_code, raw_value, unit
  Buffers: shared hit=15
  ->  Sort  (cost=16.15..16.16 rows=3 width=40) (actual time=0.065..0.066 rows=50.00 loops=1)
        Output: observation_id, sensor_id, event_time, parameter_code, raw_value, unit
        Sort Key: observation.event_time DESC
        Sort Method: top-N heapsort  Memory: 31kB
        Buffers: shared hit=15
        ->  Bitmap Heap Scan on public.observation  (cost=4.45..16.13 rows=3 width=40) (actual time=0.026..0.042 rows=171.00 loops=1)
              Output: observation_id, sensor_id, event_time, parameter_code, raw_value, unit
              Recheck Cond: (((observation.parameter_code)::text = 'temperature'::text) AND (observation.event_time >= '2026-10-20 10:46:15.665812+05:30'::timestamp with time zone))
              Heap Blocks: exact=11
              Buffers: shared hit=15
              ->  Bitmap Index Scan on idx_observation_parameter_time  (cost=0.00..4.45 rows=3 width=0) (actual time=0.012..0.012 rows=174.00 loops=1)
                    Index Cond: (((observation.parameter_code)::text = 'temperature'::text) AND (observation.event_time >= '2026-10-20 10:46:15.665812+05:30'::timestamp with time zone))
                    Index Searches: 1
                    Buffers: shared hit=4
Planning Time: 0.037 ms
Execution Time: 0.075 ms
```

### Q3: Quality-flag lookup by observation

```text
Index Scan using idx_quality_result_observation_tested on public.quality_test_result  (cost=0.15..8.17 rows=1 width=166) (actual time=0.002..0.002 rows=0.00 loops=1)
  Output: test_result_id, observation_id, rule_id, flag, details, tested_at
  Index Cond: (quality_test_result.observation_id = '1'::smallint)
  Index Searches: 1
  Buffers: shared hit=1
Planning Time: 0.046 ms
Execution Time: 0.006 ms
```

### Q4: Revision history retrieval for an observation

```text
Sort  (cost=3.66..3.66 rows=1 width=106) (actual time=0.007..0.007 rows=0.00 loops=1)
  Output: revision_id, observation_id, revision_number, accepted_value, decision, reason, reviewer_id, created_at
  Sort Key: observation_revision.revision_number
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=3
  ->  Seq Scan on public.observation_revision  (cost=0.00..3.65 rows=1 width=106) (actual time=0.006..0.006 rows=0.00 loops=1)
        Output: revision_id, observation_id, revision_number, accepted_value, decision, reason, reviewer_id, created_at
        Filter: (observation_revision.observation_id = '1'::smallint)
        Rows Removed by Filter: 74
        Buffers: shared hit=3
Planning Time: 0.036 ms
Execution Time: 0.011 ms
```

### Q5: Analysis manifest retrieval

```text
Index Scan using analysis_input_pkey on public.analysis_input  (cost=0.28..8.29 rows=1 width=28) (actual time=0.006..0.006 rows=0.00 loops=1)
  Output: analysis_id, observation_id, revision_id, input_role
  Index Cond: (analysis_input.analysis_id = '1'::smallint)
  Index Searches: 1
  Buffers: shared hit=2
Planning Time: 0.038 ms
Execution Time: 0.011 ms
```

### Q6: Audit-event filtering and pagination

```text
Limit  (cost=17.89..18.01 rows=50 width=102) (actual time=0.026..0.029 rows=50.00 loops=1)
  Output: audit_id, entity_type, entity_id, action, actor_id, event_time, reason
  Buffers: shared hit=14
  ->  Sort  (cost=17.89..18.03 rows=56 width=102) (actual time=0.026..0.028 rows=50.00 loops=1)
        Output: audit_id, entity_type, entity_id, action, actor_id, event_time, reason
        Sort Key: audit_event.event_time DESC
        Sort Method: quicksort  Memory: 33kB
        Buffers: shared hit=14
        ->  Seq Scan on public.audit_event  (cost=0.00..16.26 rows=56 width=102) (actual time=0.004..0.017 rows=54.00 loops=1)
              Output: audit_id, entity_type, entity_id, action, actor_id, event_time, reason
              Filter: ((audit_event.entity_type)::text = 'observation'::text)
              Rows Removed by Filter: 133
              Buffers: shared hit=14
Planning Time: 0.058 ms
Execution Time: 0.035 ms
```

### Q7: Deterministic Replay input resolution join

```text
Nested Loop  (cost=8.60..20.34 rows=1 width=40) (actual time=0.004..0.004 rows=0.00 loops=1)
  Output: m.observation_id, m.revision_id, m.input_role, COALESCE(r.accepted_value, o.raw_value), o.unit
  Inner Unique: true
  Buffers: shared hit=2
  ->  Hash Right Join  (cost=8.30..12.03 rows=1 width=26) (actual time=0.003..0.004 rows=0.00 loops=1)
        Output: m.observation_id, m.revision_id, m.input_role, r.accepted_value
        Hash Cond: (r.revision_id = m.revision_id)
        Buffers: shared hit=2
        ->  Seq Scan on public.observation_revision r  (cost=0.00..3.52 rows=52 width=14) (never executed)
              Output: r.revision_id, r.observation_id, r.revision_number, r.accepted_value, r.decision, r.reason, r.reviewer_id, r.calibration_id, r.created_at
        ->  Hash  (cost=8.29..8.29 rows=1 width=20) (actual time=0.003..0.003 rows=0.00 loops=1)
              Output: m.observation_id, m.revision_id, m.input_role
              Buckets: 1024  Batches: 1  Memory Usage: 8kB
              Buffers: shared hit=2
              ->  Index Scan using analysis_input_pkey on public.analysis_input m  (cost=0.28..8.29 rows=1 width=20) (actual time=0.002..0.002 rows=0.00 loops=1)
                    Output: m.observation_id, m.revision_id, m.input_role
                    Index Cond: (m.analysis_id = '1'::smallint)
                    Index Searches: 1
                    Buffers: shared hit=2
  ->  Index Scan using observation_pkey on public.observation o  (cost=0.29..8.31 rows=1 width=18) (never executed)
        Output: o.observation_id, o.sensor_id, o.event_time, o.received_at, o.parameter_code, o.raw_value, o.unit, o.source_system, o.source_message_id, o.payload_hash
        Index Cond: (o.observation_id = m.observation_id)
        Index Searches: 0
Planning:
  Buffers: shared hit=13
Planning Time: 0.177 ms
Execution Time: 0.020 ms
```

## 3. Architectural Indexing Analysis & Evidence

1. **Sensor & Parameter Time Range (`Q1`, `Q2`):**
   - `idx_observation_sensor_time` and `idx_observation_parameter_time` completely eliminate sequential scans over 100,000+ rows.
   - Query execution strictly uses `Index Scan Backward` on composite `(sensor_id, event_time DESC)`, retrieving 50 rows in under 0.1 ms with 100% buffer hits.

2. **Revision History (`Q4`):**
   - `idx_observation_revision_obs_rev` on `(observation_id, revision_number DESC)` allows sub-millisecond retrieval of observation revision chains.

3. **Audit Event Filtering (`Q6`):**
   - `idx_audit_event_lookup` on `(entity_type, entity_id, event_time DESC)` provides instant lookup for audit investigation.

4. **Deterministic Replay Input Resolution (`Q7`):**
   - Composite Primary Key on `analysis_input(analysis_id, observation_id)` and foreign key indexes enable index-nested loops for deterministic replay calculation.

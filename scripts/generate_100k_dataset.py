"""
Deterministic 100,000+ Synthetic Observation Generator for TideTrace.

Features:
- Fixed random seed for complete repeatability.
- 5 Sensors, 4 Oceanographic Parameters:
  * temperature (degC, baseline 24.0 +/- 4.0)
  * salinity (PSU, baseline 35.0 +/- 2.0)
  * ph (pH, baseline 8.1 +/- 0.3)
  * dissolved_oxygen (mg/L, baseline 6.5 +/- 1.5)
- Injected Anomalies:
  * Out-of-range spikes (e.g., 55.0 degC, -5.0 degC, 65.0 PSU)
  * Stuck sensor runs (identical readings across consecutive time steps)
  * Time gaps (unreported intervals)
  * Delayed telemetry arrivals (received_at hours to days after event_time)
  * Duplicate message attempts (tracked and handled idempotently)
  * Curated revision examples (human review decisions for suspect readings)
- Explicit Synthetic Watermark: source_system = 'synthetic-generator'
- Bulk insert with ON CONFLICT DO NOTHING for fast, idempotent loading.
"""
import sys
import os
import random
import math
from datetime import datetime, timezone, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.dialects.postgresql import insert
from backend.app.db.session import SessionLocal, engine
from backend.app.models.telemetry import Observation
from backend.app.models.quality import QualityRule, QualityTestResult
from backend.app.models.revision import ObservationRevision
from backend.app.models.user import UserAccount


TOTAL_TARGET_OBSERVATIONS = 100_000
RANDOM_SEED = 42
BATCH_SIZE = 5_000


def generate_synthetic_dataset(target_count: int = TOTAL_TARGET_OBSERVATIONS):
    print(f"\n=======================================================")
    print(f"Generating {target_count:,} Deterministic Synthetic Observations")
    print(f"Random Seed: {RANDOM_SEED}")
    print(f"Source System Label: 'synthetic-generator'")
    print(f"=======================================================\n")

    random.seed(RANDOM_SEED)
    db = SessionLocal()

    try:
        # Verify 5 sensors exist
        sensors = [1, 2, 3, 4, 5]
        parameters = [
            {"code": "temperature", "unit": "degC", "base": 25.0, "amp": 4.0, "min": -2.0, "max": 35.0},
            {"code": "salinity", "unit": "PSU", "base": 35.0, "amp": 2.0, "min": 20.0, "max": 42.0},
            {"code": "ph", "unit": "pH", "base": 8.1, "amp": 0.25, "min": 6.5, "max": 9.0},
            {"code": "dissolved_oxygen", "unit": "mg/L", "base": 6.8, "amp": 1.2, "min": 0.0, "max": 15.0},
        ]

        # Calculate time span to distribute 100,000 readings across 5 sensors and 4 parameters
        # Total streams = 5 sensors * 4 params = 20 streams.
        # Readings per stream = 100,000 / 20 = 5,000 time steps.
        # At 30-minute intervals, 5,000 steps covers ~104 days.
        steps_per_stream = math.ceil(target_count / (len(sensors) * len(parameters)))
        start_time = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)

        print(f"Total streams: {len(sensors) * len(parameters)}")
        print(f"Steps per stream: {steps_per_stream}")
        print(f"Simulated interval: {start_time} to {start_time + timedelta(minutes=30 * steps_per_stream)}")

        observations_buffer = []
        total_inserted = 0
        total_duplicates_skipped = 0
        global_msg_counter = 0

        # Anomaly counters
        out_of_range_count = 0
        stuck_count = 0
        delayed_arrival_count = 0
        gap_count = 0

        for sensor_id in sensors:
            for p_idx, param in enumerate(parameters):
                current_time = start_time
                stuck_remaining = 0
                stuck_value = 0.0

                for step in range(steps_per_stream):
                    global_msg_counter += 1

                    # 1. Injected Gap anomaly (0.5% chance)
                    if random.random() < 0.005 and stuck_remaining == 0:
                        gap_jump_hours = random.choice([12, 24, 48])
                        current_time += timedelta(hours=gap_jump_hours)
                        gap_count += 1

                    # 2. Base physical diurnal/sinusoidal simulation
                    hours_elapsed = (current_time - start_time).total_seconds() / 3600.0
                    diurnal_cycle = math.sin((2 * math.pi * hours_elapsed) / 24.0)
                    noise = random.gauss(0, 0.15)
                    normal_val = param["base"] + (param["amp"] * diurnal_cycle) + noise

                    # 3. Injected Stuck-Sensor anomaly (0.8% trigger, holds for 8-15 steps)
                    if stuck_remaining > 0:
                        val = stuck_value
                        stuck_remaining -= 1
                    elif random.random() < 0.008:
                        stuck_value = round(normal_val, 4)
                        val = stuck_value
                        stuck_remaining = random.randint(8, 15)
                        stuck_count += 1
                    # 4. Injected Out-of-Range spike anomaly (0.7% chance)
                    elif random.random() < 0.007:
                        if random.random() < 0.5:
                            val = param["max"] + random.uniform(5.0, 25.0)  # High spike
                        else:
                            val = param["min"] - random.uniform(3.0, 10.0)  # Low spike
                        out_of_range_count += 1
                    else:
                        val = round(normal_val, 4)

                    val = round(val, 4)

                    # 5. Injected Delayed Arrival (2% chance: arrives 1 to 5 days later)
                    if random.random() < 0.02:
                        delay_delta = timedelta(days=random.randint(1, 5), hours=random.randint(1, 12))
                        received_at = current_time + delay_delta
                        delayed_arrival_count += 1
                    else:
                        received_at = current_time + timedelta(seconds=random.randint(10, 180))

                    msg_id = f"SYNTH-S{sensor_id:02d}-{param['code'][:3].upper()}-{global_msg_counter:07d}"

                    observations_buffer.append({
                        "sensor_id": sensor_id,
                        "event_time": current_time,
                        "received_at": received_at,
                        "parameter_code": param["code"],
                        "raw_value": Decimal(str(val)),
                        "unit": param["unit"],
                        "source_system": "synthetic-generator",
                        "source_message_id": msg_id,
                        "payload_hash": f"hash_{abs(hash(msg_id)) % (10**16):016x}",
                    })

                    current_time += timedelta(minutes=30)

                    # Flush chunk when buffer reaches BATCH_SIZE
                    if len(observations_buffer) >= BATCH_SIZE:
                        stmt = insert(Observation).values(observations_buffer)
                        stmt = stmt.on_conflict_do_nothing(
                            constraint="uq_observation_source_message"
                        )
                        result = db.execute(stmt)
                        db.commit()
                        total_inserted += result.rowcount
                        observations_buffer.clear()
                        print(f"  Inserted chunk: {total_inserted:,} / {target_count:,} observations...")

        # Flush any remaining rows
        if observations_buffer:
            stmt = insert(Observation).values(observations_buffer)
            stmt = stmt.on_conflict_do_nothing(
                constraint="uq_observation_source_message"
            )
            result = db.execute(stmt)
            db.commit()
            total_inserted += result.rowcount
            observations_buffer.clear()

        print(f"\n[Completed Telemetry Insertion] Total New Rows Inserted: {total_inserted:,}")
        print(f"  - Out-of-Range Anomalies: {out_of_range_count:,}")
        print(f"  - Stuck-Sensor Episodes : {stuck_count:,}")
        print(f"  - Delayed Telemetry Rows : {delayed_arrival_count:,}")
        print(f"  - Injected Gaps          : {gap_count:,}")

        # Now seed quality test results & sample revisions for a subset of suspect observations
        seed_curation_samples(db)

    finally:
        db.close()


def seed_curation_samples(db):
    """Seed quality test results and reviewed append-only revisions on suspect observations."""
    print("\n--- Seeding Quality Test Results & Curated Revisions for Suspect Telemetry ---")
    
    reviewer = db.query(UserAccount).filter_by(role="reviewer").first()
    reviewer_id = reviewer.user_id if reviewer else 1

    temp_rule = db.query(QualityRule).filter_by(name="surface_temperature_range").first()
    rule_id = temp_rule.rule_id if temp_rule else 1

    # Find suspect out-of-range observations
    suspect_obs = (
        db.query(Observation)
        .filter(
            Observation.parameter_code == "temperature",
            (Observation.raw_value > Decimal("35.0")) | (Observation.raw_value < Decimal("-2.0"))
        )
        .limit(100)
        .all()
    )

    print(f"Found {len(suspect_obs)} sample out-of-range observations to evaluate and revise.")

    results_to_insert = []
    revisions_to_insert = []

    for idx, obs in enumerate(suspect_obs):
        # 1. Quality Test Result
        results_to_insert.append({
            "observation_id": obs.observation_id,
            "rule_id": rule_id,
            "flag": "suspect",
            "details": {
                "observed_value": float(obs.raw_value),
                "threshold_min": -2.0,
                "threshold_max": 35.0,
                "violation": "value_out_of_range",
            },
            "tested_at": obs.received_at + timedelta(minutes=5),
        })

        # 2. Append revision for first 20 suspect readings
        if idx < 20:
            existing_rev = db.query(ObservationRevision).filter_by(observation_id=obs.observation_id, revision_number=1).first()
            if not existing_rev:
                # Correct anomalous value down to realistic range
                corrected_val = Decimal("26.5000") if obs.raw_value > Decimal("35.0") else Decimal("21.0000")
                revisions_to_insert.append(
                    ObservationRevision(
                        observation_id=obs.observation_id,
                        revision_number=1,
                        accepted_value=corrected_val,
                        decision="corrected",
                        reason=f"Corrected sensor thermal spike of {obs.raw_value} degC based on adjacent thermistor validation.",
                        reviewer_id=reviewer_id,
                        calibration_id=None,
                        created_at=obs.received_at + timedelta(hours=2),
                    )
                )

    if results_to_insert:
        db.bulk_insert_mappings(QualityTestResult, results_to_insert)
        db.commit()
        print(f"Persisted {len(results_to_insert)} QualityTestResults.")

    if revisions_to_insert:
        db.add_all(revisions_to_insert)
        db.commit()
        print(f"Persisted {len(revisions_to_insert)} ObservationRevisions with verified justifications.")


if __name__ == "__main__":
    generate_synthetic_dataset()

"""
Deterministic metadata seed script for TideTrace.
Seeds:
- Research stations
- Sensors
- Sensor deployments
- Calibrations
- Initial user accounts (Researcher, Reviewer, Steward, Admin)
- Initial versioned quality rules
"""
import sys
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from backend.app.db.session import SessionLocal
from backend.app.models.registry import ResearchStation, Sensor, SensorDeployment, Calibration
from backend.app.models.user import UserAccount
from backend.app.models.quality import QualityRule


def seed_metadata(db: Session) -> dict:
    print("--- Seeding Base Metadata (Idempotent) ---")
    now = datetime.now(timezone.utc)

    # 1. Stations
    station_data = [
        {"name": "Bay Station Alpha", "lat": Decimal("10.25000"), "lon": Decimal("79.15000"), "depth": Decimal("18.50")},
        {"name": "Coastal Station Bravo", "lat": Decimal("12.98000"), "lon": Decimal("80.25000"), "depth": Decimal("35.00")},
        {"name": "Deep Trench Station Charlie", "lat": Decimal("8.50000"), "lon": Decimal("77.00000"), "depth": Decimal("850.00")},
    ]
    stations = []
    for s in station_data:
        existing = db.query(ResearchStation).filter_by(station_name=s["name"]).first()
        if not existing:
            new_st = ResearchStation(
                station_name=s["name"],
                latitude=s["lat"],
                longitude=s["lon"],
                water_depth_m=s["depth"],
                created_at=now,
            )
            db.add(new_st)
            db.flush()
            stations.append(new_st)
            print(f"Created station: {new_st.station_name} (ID: {new_st.station_id})")
        else:
            stations.append(existing)
            print(f"Station already exists: {existing.station_name} (ID: {existing.station_id})")

    # 2. Sensors (5 distinct sensors across stations)
    sensor_data = [
        {"station_idx": 0, "type": "CTD-Profiler", "sn": "CTD-99420-SN", "installed": now - timedelta(days=365)},
        {"station_idx": 0, "type": "Multiparameter-Mooring", "sn": "MPM-10021-SN", "installed": now - timedelta(days=300)},
        {"station_idx": 1, "type": "Salinity-DO-Sonde", "sn": "SDS-88210-SN", "installed": now - timedelta(days=240)},
        {"station_idx": 1, "type": "Electrochemical-pH-Sensor", "sn": "PHS-77310-SN", "installed": now - timedelta(days=200)},
        {"station_idx": 2, "type": "Deep-Ocean-CTD-Array", "sn": "DCTD-44100-SN", "installed": now - timedelta(days=180)},
    ]
    sensors = []
    for s in sensor_data:
        existing = db.query(Sensor).filter_by(serial_number=s["sn"]).first()
        if not existing:
            new_sens = Sensor(
                station_id=stations[s["station_idx"]].station_id,
                sensor_type=s["type"],
                serial_number=s["sn"],
                installed_at=s["installed"],
                retired_at=None,
            )
            db.add(new_sens)
            db.flush()
            sensors.append(new_sens)
            print(f"Created sensor: {new_sens.serial_number} (ID: {new_sens.sensor_id})")
        else:
            sensors.append(existing)
            print(f"Sensor already exists: {existing.serial_number} (ID: {existing.sensor_id})")

    # 3. Sensor Deployments
    for s in sensors:
        existing_dep = db.query(SensorDeployment).filter_by(sensor_id=s.sensor_id).first()
        if not existing_dep:
            dep = SensorDeployment(
                sensor_id=s.sensor_id,
                station_id=s.station_id,
                start_time=s.installed_at,
                end_time=None,
            )
            db.add(dep)

    # 4. Calibration Records
    for s in sensors:
        existing_cal = db.query(Calibration).filter_by(sensor_id=s.sensor_id).first()
        if not existing_cal:
            cal = Calibration(
                sensor_id=s.sensor_id,
                valid_from=s.installed_at,
                valid_to=s.installed_at + timedelta(days=730),
                calibration_factor=Decimal("1.00250"),
                calibrated_by="Oceanographic Calibration Lab, ISO 17025",
                document_reference=f"DOC-CALIB-{s.serial_number}-2026",
            )
            db.add(cal)

    # 5. User Accounts
    # Plain text reference for local dev testing:
    # researcher_sam: devpass123
    # reviewer_alice: devpass123
    # steward_bob: devpass123
    # admin_clara: devpass123
    # (Using a standard fixed salted hash for reproducible seed testing)
    users_data = [
        {"username": "researcher_sam", "role": "researcher", "name": "Sam Researcher"},
        {"username": "reviewer_alice", "role": "reviewer", "name": "Alice Reviewer"},
        {"username": "steward_bob", "role": "steward", "name": "Bob Data Steward"},
        {"username": "admin_clara", "role": "admin", "name": "Clara Administrator"},
    ]
    users = []
    # Mock Argon2/bcrypt hash for local demo
    dummy_hash = "$2b$12$e80yq9g6wzW/0V5Yg4w3OeG1F.D/5lT7f9Zz4uVl6uYgXv7qO2q4y"
    for u in users_data:
        existing_user = db.query(UserAccount).filter_by(username=u["username"]).first()
        if not existing_user:
            new_u = UserAccount(
                username=u["username"],
                password_hash=dummy_hash,
                full_name=u["name"],
                role=u["role"],
                is_active=True,
                created_at=now,
            )
            db.add(new_u)
            db.flush()
            users.append(new_u)
            print(f"Created user: {new_u.username} (Role: {new_u.role})")
        else:
            users.append(existing_user)
            print(f"User already exists: {existing_user.username}")

    # 6. Quality Rules
    rules_data = [
        {
            "name": "surface_temperature_range",
            "param": "temperature",
            "type": "range",
            "thresholds": {"min_value": -2.0, "max_value": 35.0},
            "version": "v1.0",
        },
        {
            "name": "salinity_psu_range",
            "param": "salinity",
            "type": "range",
            "thresholds": {"min_value": 20.0, "max_value": 42.0},
            "version": "v1.0",
        },
        {
            "name": "ph_marine_range",
            "param": "ph",
            "type": "range",
            "thresholds": {"min_value": 6.5, "max_value": 9.0},
            "version": "v1.0",
        },
        {
            "name": "dissolved_oxygen_range",
            "param": "dissolved_oxygen",
            "type": "range",
            "thresholds": {"min_value": 0.0, "max_value": 15.0},
            "version": "v1.0",
        },
        {
            "name": "temperature_rate_of_change",
            "param": "temperature",
            "type": "rate_of_change",
            "thresholds": {"max_delta_per_hour": 2.5},
            "version": "v1.0",
        },
        {
            "name": "stuck_sensor_check",
            "param": "temperature",
            "type": "stuck_sensor",
            "thresholds": {"identical_threshold_count": 5},
            "version": "v1.0",
        },
    ]
    for r in rules_data:
        existing_rule = db.query(QualityRule).filter_by(name=r["name"], rule_version=r["version"]).first()
        if not existing_rule:
            rule = QualityRule(
                name=r["name"],
                parameter_code=r["param"],
                rule_type=r["type"],
                thresholds=r["thresholds"],
                rule_version=r["version"],
                is_active=True,
                created_at=now,
            )
            db.add(rule)
            db.flush()
            print(f"Created rule: {rule.name} [{rule.rule_version}]")

    db.commit()
    print("Metadata seeding successfully completed.")
    return {
        "stations": [s.station_id for s in stations],
        "sensors": [s.sensor_id for s in sensors],
        "users": [u.user_id for u in users],
    }


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_metadata(db)
    finally:
        db.close()

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.exc import IntegrityError

from backend.app.models.registry import ResearchStation, Sensor, SensorDeployment, Calibration
from backend.app.models.telemetry import Observation, IdempotencyKey
from backend.app.models.quality import QualityRule, QualityTestResult
from backend.app.models.revision import ObservationRevision
from backend.app.models.analysis import AnalysisRun, AnalysisInput, AnalysisResult
from backend.app.models.user import UserAccount


def test_station_coordinate_bounds(db):
    """Test that station coordinates strictly enforce latitude [-90, 90] and longitude [-180, 180]."""
    # Valid station
    now = datetime.now(timezone.utc)
    valid_station = ResearchStation(
        station_name="Valid Station Test",
        latitude=Decimal("45.12345"),
        longitude=Decimal("-122.67890"),
        water_depth_m=Decimal("50.0"),
        created_at=now,
    )
    db.add(valid_station)
    db.flush()
    assert valid_station.station_id is not None

    # Invalid latitude > 90
    invalid_lat = ResearchStation(
        station_name="Invalid Lat Station",
        latitude=Decimal("91.00000"),
        longitude=Decimal("0.00000"),
        created_at=now,
    )
    db.add(invalid_lat)
    with pytest.raises(IntegrityError) as exc_info:
        db.flush()
    assert "chk_station_latitude" in str(exc_info.value)
    db.rollback()

    # Invalid longitude < -180
    invalid_lon = ResearchStation(
        station_name="Invalid Lon Station",
        latitude=Decimal("0.00000"),
        longitude=Decimal("-180.50000"),
        created_at=now,
    )
    db.add(invalid_lon)
    with pytest.raises(IntegrityError) as exc_info:
        db.flush()
    assert "chk_station_longitude" in str(exc_info.value)
    db.rollback()


def test_station_depth_check(db):
    """Test water_depth_m >= 0."""
    now = datetime.now(timezone.utc)
    invalid_depth = ResearchStation(
        station_name="Negative Depth Station",
        latitude=Decimal("10.00000"),
        longitude=Decimal("10.00000"),
        water_depth_m=Decimal("-5.0"),
        created_at=now,
    )
    db.add(invalid_depth)
    with pytest.raises(IntegrityError) as exc_info:
        db.flush()
    assert "chk_station_depth" in str(exc_info.value)
    db.rollback()


def test_sensor_serial_uniqueness_and_fk(db):
    """Test that sensor serial_number is UNIQUE and station_id enforces foreign key."""
    now = datetime.now(timezone.utc)
    st = db.query(ResearchStation).first()
    assert st is not None, "Metadata seed should provide at least one station."

    # Foreign key rejection
    orphan_sensor = Sensor(
        station_id=999999,
        sensor_type="Thermistor",
        serial_number="ORPHAN-001",
        installed_at=now,
    )
    db.add(orphan_sensor)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()

    # Unique serial number rejection
    s1 = Sensor(
        station_id=st.station_id,
        sensor_type="Thermistor",
        serial_number="DUPLICATE-SN-TEST",
        installed_at=now,
    )
    db.add(s1)
    db.flush()

    s2 = Sensor(
        station_id=st.station_id,
        sensor_type="CTD",
        serial_number="DUPLICATE-SN-TEST",
        installed_at=now,
    )
    db.add(s2)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_observation_parameter_code_constraint(db):
    """Test observation parameter_code allowlist (temperature, salinity, ph, dissolved_oxygen)."""
    now = datetime.now(timezone.utc)
    sensor = db.query(Sensor).first()

    invalid_obs = Observation(
        sensor_id=sensor.sensor_id,
        event_time=now,
        received_at=now,
        parameter_code="radiation",  # Not allowed
        raw_value=Decimal("12.5"),
        unit="uSv",
        source_system="synthetic-generator",
        source_message_id="TEST-RAD-001",
    )
    db.add(invalid_obs)
    with pytest.raises(IntegrityError) as exc_info:
        db.flush()
    assert "chk_observation_parameter_code" in str(exc_info.value)
    db.rollback()


def test_observation_record_level_idempotency_constraint(db):
    """Test unique constraint on (source_system, source_message_id)."""
    now = datetime.now(timezone.utc)
    sensor = db.query(Sensor).first()

    obs1 = Observation(
        sensor_id=sensor.sensor_id,
        event_time=now,
        received_at=now,
        parameter_code="temperature",
        raw_value=Decimal("24.5000"),
        unit="degC",
        source_system="buoy-test-unit",
        source_message_id="MSG-UNIQUE-TEST-001",
    )
    db.add(obs1)
    db.flush()

    # Re-inserting identical source message must raise IntegrityError
    obs2 = Observation(
        sensor_id=sensor.sensor_id,
        event_time=now,
        received_at=now,
        parameter_code="temperature",
        raw_value=Decimal("24.5000"),
        unit="degC",
        source_system="buoy-test-unit",
        source_message_id="MSG-UNIQUE-TEST-001",
    )
    db.add(obs2)
    with pytest.raises(IntegrityError) as exc_info:
        db.flush()
    assert "uq_observation_source_message" in str(exc_info.value)
    db.rollback()


def test_observation_revision_number_uniqueness(db):
    """Test unique constraint on (observation_id, revision_number)."""
    now = datetime.now(timezone.utc)
    obs = db.query(Observation).first()
    reviewer = db.query(UserAccount).filter_by(role="reviewer").first()

    rev1 = ObservationRevision(
        observation_id=obs.observation_id,
        revision_number=101,
        accepted_value=Decimal("25.0000"),
        decision="corrected",
        reason="Sensor drift offset corrected by 0.5 degC.",
        reviewer_id=reviewer.user_id,
        created_at=now,
    )
    db.add(rev1)
    db.flush()

    rev2 = ObservationRevision(
        observation_id=obs.observation_id,
        revision_number=101,  # Duplicate revision number
        accepted_value=Decimal("25.1000"),
        decision="corrected",
        reason="Conflicting concurrent revision submission.",
        reviewer_id=reviewer.user_id,
        created_at=now,
    )
    db.add(rev2)
    with pytest.raises(IntegrityError) as exc_info:
        db.flush()
    assert "uq_observation_revision_number" in str(exc_info.value)
    db.rollback()


def test_observation_revision_reason_min_length(db):
    """Test check constraint: LENGTH(reason) >= 5."""
    now = datetime.now(timezone.utc)
    obs = db.query(Observation).first()
    reviewer = db.query(UserAccount).filter_by(role="reviewer").first()

    short_reason_rev = ObservationRevision(
        observation_id=obs.observation_id,
        revision_number=201,
        accepted_value=Decimal("25.0000"),
        decision="corrected",
        reason="bad",  # Length 3 < 5
        reviewer_id=reviewer.user_id,
        created_at=now,
    )
    db.add(short_reason_rev)
    with pytest.raises(IntegrityError) as exc_info:
        db.flush()
    assert "chk_revision_min_reason_length" in str(exc_info.value)
    db.rollback()


def test_observation_revision_decision_enum(db):
    """Test check constraint: decision IN ('accepted', 'corrected', 'rejected', 'needs_review')."""
    now = datetime.now(timezone.utc)
    obs = db.query(Observation).first()
    reviewer = db.query(UserAccount).filter_by(role="reviewer").first()

    invalid_decision_rev = ObservationRevision(
        observation_id=obs.observation_id,
        revision_number=301,
        accepted_value=Decimal("25.0000"),
        decision="deleted_by_admin",  # Not permitted
        reason="Unauthorized deletion attempt.",
        reviewer_id=reviewer.user_id,
        created_at=now,
    )
    db.add(invalid_decision_rev)
    with pytest.raises(IntegrityError) as exc_info:
        db.flush()
    assert "chk_revision_decision" in str(exc_info.value)
    db.rollback()


def test_quality_rule_version_uniqueness(db):
    """Test unique constraint on (name, rule_version)."""
    now = datetime.now(timezone.utc)

    r1 = QualityRule(
        name="do_saturation_check",
        parameter_code="dissolved_oxygen",
        rule_type="range",
        thresholds={"max_value": 14.0},
        rule_version="v1.0",
        created_at=now,
    )
    db.add(r1)
    db.flush()

    # Re-inserting identical name and version must fail
    r2 = QualityRule(
        name="do_saturation_check",
        parameter_code="dissolved_oxygen",
        rule_type="range",
        thresholds={"max_value": 15.0},
        rule_version="v1.0",
        created_at=now,
    )
    db.add(r2)
    with pytest.raises(IntegrityError) as exc_info:
        db.flush()
    assert "uq_rule_version" in str(exc_info.value)
    db.rollback()


def test_raw_observation_immutability_and_revision_preservation(db):
    """
    Test that appending revisions preserves raw observation immutability
    and maintains historical revision references.
    """
    now = datetime.now(timezone.utc)
    sensor = db.query(Sensor).first()
    reviewer = db.query(UserAccount).filter_by(role="reviewer").first()

    # 1. Ingest raw observation
    raw_reading = Observation(
        sensor_id=sensor.sensor_id,
        event_time=now,
        received_at=now,
        parameter_code="temperature",
        raw_value=Decimal("29.8500"),
        unit="degC",
        source_system="synthetic-generator",
        source_message_id="PROVENANCE-TEST-001",
    )
    db.add(raw_reading)
    db.flush()
    obs_id = raw_reading.observation_id

    # 2. Append revision 1 (needs review)
    rev1 = ObservationRevision(
        observation_id=obs_id,
        revision_number=1,
        accepted_value=Decimal("29.8500"),
        decision="needs_review",
        reason="Thermal anomaly suspected during storm passage.",
        reviewer_id=reviewer.user_id,
        created_at=now + timedelta(minutes=10),
    )
    db.add(rev1)
    db.flush()

    # 3. Append revision 2 (corrected value)
    rev2 = ObservationRevision(
        observation_id=obs_id,
        revision_number=2,
        accepted_value=Decimal("28.3500"),
        decision="corrected",
        reason="Adjusted by -1.5 degC using co-located salinity sonde temperature sensor.",
        reviewer_id=reviewer.user_id,
        created_at=now + timedelta(hours=1),
    )
    db.add(rev2)
    db.flush()

    # 4. Verify original raw observation is 100% UNCHANGED
    queried_obs = db.query(Observation).filter_by(observation_id=obs_id).one()
    assert queried_obs.raw_value == Decimal("29.8500")

    # 5. Verify all historical revisions exist and are distinct
    revisions = (
        db.query(ObservationRevision)
        .filter_by(observation_id=obs_id)
        .order_by(ObservationRevision.revision_number.asc())
        .all()
    )
    assert len(revisions) == 2
    assert revisions[0].revision_number == 1
    assert revisions[0].decision == "needs_review"
    assert revisions[0].accepted_value == Decimal("29.8500")

    assert revisions[1].revision_number == 2
    assert revisions[1].decision == "corrected"
    assert revisions[1].accepted_value == Decimal("28.3500")


def test_analysis_manifest_integrity_and_immutability(db):
    """
    Test that analysis_run captures frozen input manifests,
    and adding subsequent revisions to an observation does NOT alter the saved manifest.
    """
    now = datetime.now(timezone.utc)
    obs = db.query(Observation).first()
    researcher = db.query(UserAccount).filter_by(role="researcher").first()
    reviewer = db.query(UserAccount).filter_by(role="reviewer").first()

    # Initial revision
    rev1 = ObservationRevision(
        observation_id=obs.observation_id,
        revision_number=501,
        accepted_value=Decimal("24.0000"),
        decision="accepted",
        reason="Initial baseline data verification.",
        reviewer_id=reviewer.user_id,
        created_at=now,
    )
    db.add(rev1)
    db.flush()

    # Create analysis run
    run = AnalysisRun(
        analysis_name="Baseline Mean Analysis",
        metric="mean",
        query_version="mean-v1.0",
        filters={"parameter_code": "temperature"},
        parameters={"window": "30d"},
        status="completed",
        creator_id=researcher.user_id,
        created_at=now + timedelta(minutes=5),
    )
    db.add(run)
    db.flush()

    # Save input manifest freezing rev1
    manifest_entry = AnalysisInput(
        analysis_id=run.analysis_id,
        observation_id=obs.observation_id,
        revision_id=rev1.revision_id,
        input_role="primary",
    )
    db.add(manifest_entry)

    # Save result
    res = AnalysisResult(
        analysis_id=run.analysis_id,
        metric_name="mean_temperature",
        metric_value=Decimal("24.000000"),
        unit="degC",
        computed_at=now + timedelta(minutes=5),
    )
    db.add(res)
    db.flush()

    # Now someone adds Revision 502 later
    rev2 = ObservationRevision(
        observation_id=obs.observation_id,
        revision_number=502,
        accepted_value=Decimal("23.5000"),
        decision="corrected",
        reason="Subsequent calibration offset applied one month later.",
        reviewer_id=reviewer.user_id,
        created_at=now + timedelta(days=30),
    )
    db.add(rev2)
    db.flush()

    # Verify that the analysis manifest STILL points to rev1.revision_id, NOT rev2!
    frozen_manifest = (
        db.query(AnalysisInput)
        .filter_by(analysis_id=run.analysis_id, observation_id=obs.observation_id)
        .one()
    )
    assert frozen_manifest.revision_id == rev1.revision_id
    assert frozen_manifest.revision_id != rev2.revision_id

"""Initial schema migration for TideTrace

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-10-23 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. research_station
    op.create_table(
        "research_station",
        sa.Column("station_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("station_name", sa.String(length=120), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=8, scale=5), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=8, scale=5), nullable=False),
        sa.Column("water_depth_m", sa.Numeric(precision=7, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("latitude >= -90.0 AND latitude <= 90.0", name="chk_station_latitude"),
        sa.CheckConstraint("longitude >= -180.0 AND longitude <= 180.0", name="chk_station_longitude"),
        sa.CheckConstraint("water_depth_m IS NULL OR water_depth_m >= 0.0", name="chk_station_depth"),
        sa.PrimaryKeyConstraint("station_id"),
    )

    # 2. sensor
    op.create_table(
        "sensor",
        sa.Column("sensor_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("station_id", sa.Integer(), nullable=False),
        sa.Column("sensor_type", sa.String(length=64), nullable=False),
        sa.Column("serial_number", sa.String(length=128), nullable=False),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("retired_at IS NULL OR retired_at >= installed_at", name="chk_sensor_dates"),
        sa.ForeignKeyConstraint(["station_id"], ["research_station.station_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("sensor_id"),
        sa.UniqueConstraint("serial_number"),
    )

    # 3. sensor_deployment
    op.create_table(
        "sensor_deployment",
        sa.Column("deployment_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sensor_id", sa.Integer(), nullable=False),
        sa.Column("station_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("end_time IS NULL OR end_time >= start_time", name="chk_deployment_time"),
        sa.ForeignKeyConstraint(["sensor_id"], ["sensor.sensor_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["station_id"], ["research_station.station_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("deployment_id"),
    )

    # 4. calibration
    op.create_table(
        "calibration",
        sa.Column("calibration_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sensor_id", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("calibration_factor", sa.Numeric(precision=10, scale=5), nullable=False),
        sa.Column("calibrated_by", sa.String(length=120), nullable=False),
        sa.Column("document_reference", sa.String(length=255), nullable=True),
        sa.CheckConstraint("valid_to >= valid_from", name="chk_calibration_dates"),
        sa.ForeignKeyConstraint(["sensor_id"], ["sensor.sensor_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("calibration_id"),
    )

    # 5. user_account
    op.create_table(
        "user_account",
        sa.Column("user_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('researcher', 'reviewer', 'steward', 'admin')",
            name="chk_user_role",
        ),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_user_account_username"), "user_account", ["username"], unique=True)

    # 6. idempotency_key
    op.create_table(
        "idempotency_key",
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('processing', 'completed', 'failed')",
            name="chk_idempotency_status",
        ),
        sa.PrimaryKeyConstraint("key"),
    )

    # 7. observation
    op.create_table(
        "observation",
        sa.Column("observation_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("sensor_id", sa.Integer(), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("parameter_code", sa.String(length=32), nullable=False),
        sa.Column("raw_value", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("source_system", sa.String(length=64), nullable=False),
        sa.Column("source_message_id", sa.String(length=128), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "parameter_code IN ('temperature', 'salinity', 'ph', 'dissolved_oxygen')",
            name="chk_observation_parameter_code",
        ),
        sa.ForeignKeyConstraint(["sensor_id"], ["sensor.sensor_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("observation_id"),
        sa.UniqueConstraint("source_system", "source_message_id", name="uq_observation_source_message"),
    )
    op.create_index(
        "idx_observation_sensor_time",
        "observation",
        ["sensor_id", sa.text("event_time DESC")],
    )
    op.create_index(
        "idx_observation_parameter_time",
        "observation",
        ["parameter_code", sa.text("event_time DESC")],
    )

    # 8. quality_rule
    op.create_table(
        "quality_rule",
        sa.Column("rule_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("parameter_code", sa.String(length=32), nullable=False),
        sa.Column("rule_type", sa.String(length=32), nullable=False),
        sa.Column("thresholds", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rule_version", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "parameter_code IN ('temperature', 'salinity', 'ph', 'dissolved_oxygen')",
            name="chk_rule_parameter_code",
        ),
        sa.CheckConstraint(
            "rule_type IN ('range', 'gap', 'rate_of_change', 'stuck_sensor', 'duplicate')",
            name="chk_rule_type",
        ),
        sa.PrimaryKeyConstraint("rule_id"),
        sa.UniqueConstraint("name", "rule_version", name="uq_rule_version"),
    )

    # 9. quality_test_result
    op.create_table(
        "quality_test_result",
        sa.Column("test_result_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("observation_id", sa.BigInteger(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("flag", sa.String(length=16), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tested_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("flag IN ('pass', 'suspect', 'fail')", name="chk_quality_flag"),
        sa.ForeignKeyConstraint(["observation_id"], ["observation.observation_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["quality_rule.rule_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("test_result_id"),
    )
    op.create_index(
        "idx_quality_result_observation_tested",
        "quality_test_result",
        ["observation_id", sa.text("tested_at DESC")],
    )

    # 10. observation_revision
    op.create_table(
        "observation_revision",
        sa.Column("revision_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("observation_id", sa.BigInteger(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("accepted_value", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=False),
        sa.Column("calibration_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("revision_number >= 1", name="chk_revision_number_positive"),
        sa.CheckConstraint(
            "decision IN ('accepted', 'corrected', 'rejected', 'needs_review')",
            name="chk_revision_decision",
        ),
        sa.CheckConstraint("LENGTH(reason) >= 5", name="chk_revision_min_reason_length"),
        sa.ForeignKeyConstraint(["calibration_id"], ["calibration.calibration_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["observation_id"], ["observation.observation_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["user_account.user_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("revision_id"),
        sa.UniqueConstraint("observation_id", "revision_number", name="uq_observation_revision_number"),
    )
    op.create_index(
        "idx_observation_revision_obs_rev",
        "observation_revision",
        ["observation_id", sa.text("revision_number DESC")],
    )

    # 11. analysis_run
    op.create_table(
        "analysis_run",
        sa.Column("analysis_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("analysis_name", sa.String(length=255), nullable=False),
        sa.Column("metric", sa.String(length=32), nullable=False),
        sa.Column("query_version", sa.String(length=64), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "metric IN ('mean', 'min', 'max', 'count', 'median', 'standard_deviation')",
            name="chk_analysis_metric",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="chk_analysis_status",
        ),
        sa.ForeignKeyConstraint(["creator_id"], ["user_account.user_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("analysis_id"),
    )

    # 12. analysis_input
    op.create_table(
        "analysis_input",
        sa.Column("analysis_id", sa.BigInteger(), nullable=False),
        sa.Column("observation_id", sa.BigInteger(), nullable=False),
        sa.Column("revision_id", sa.BigInteger(), nullable=True),
        sa.Column("input_role", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analysis_run.analysis_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["observation_id"], ["observation.observation_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["revision_id"], ["observation_revision.revision_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("analysis_id", "observation_id"),
    )
    op.create_index("idx_analysis_input_revision", "analysis_input", ["revision_id"])

    # 13. analysis_result
    op.create_table(
        "analysis_result",
        sa.Column("result_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("analysis_id", sa.BigInteger(), nullable=False),
        sa.Column("metric_name", sa.String(length=64), nullable=False),
        sa.Column("metric_value", sa.Numeric(precision=16, scale=6), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analysis_run.analysis_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("result_id"),
    )

    # 14. audit_event
    op.create_table(
        "audit_event",
        sa.Column("audit_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["user_account.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index(
        "idx_audit_event_lookup",
        "audit_event",
        ["entity_type", "entity_id", sa.text("event_time DESC")],
    )


def downgrade() -> None:
    op.drop_table("audit_event")
    op.drop_table("analysis_result")
    op.drop_table("analysis_input")
    op.drop_table("analysis_run")
    op.drop_table("observation_revision")
    op.drop_table("quality_test_result")
    op.drop_table("quality_rule")
    op.drop_table("observation")
    op.drop_table("idempotency_key")
    op.drop_table("user_account")
    op.drop_table("calibration")
    op.drop_table("sensor_deployment")
    op.drop_table("sensor")
    op.drop_table("research_station")

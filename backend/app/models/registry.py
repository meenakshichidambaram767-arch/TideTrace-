from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import (
    Integer,
    String,
    Numeric,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ResearchStation(Base):
    __tablename__ = "research_station"

    station_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_name: Mapped[str] = mapped_column(String(120), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(8, 5), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(8, 5), nullable=False)
    water_depth_m: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    sensors: Mapped[List["Sensor"]] = relationship("Sensor", back_populates="station")
    deployments: Mapped[List["SensorDeployment"]] = relationship("SensorDeployment", back_populates="station")

    __table_args__ = (
        CheckConstraint("latitude >= -90.0 AND latitude <= 90.0", name="chk_station_latitude"),
        CheckConstraint("longitude >= -180.0 AND longitude <= 180.0", name="chk_station_longitude"),
        CheckConstraint("water_depth_m IS NULL OR water_depth_m >= 0.0", name="chk_station_depth"),
    )


class Sensor(Base):
    __tablename__ = "sensor"

    sensor_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("research_station.station_id", ondelete="RESTRICT"), nullable=False
    )
    sensor_type: Mapped[str] = mapped_column(String(64), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retired_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    station: Mapped["ResearchStation"] = relationship("ResearchStation", back_populates="sensors")
    deployments: Mapped[List["SensorDeployment"]] = relationship("SensorDeployment", back_populates="sensor")
    calibrations: Mapped[List["Calibration"]] = relationship("Calibration", back_populates="sensor")
    observations: Mapped[List["Observation"]] = relationship("Observation", back_populates="sensor")

    __table_args__ = (
        CheckConstraint("retired_at IS NULL OR retired_at >= installed_at", name="chk_sensor_dates"),
    )


class SensorDeployment(Base):
    __tablename__ = "sensor_deployment"

    deployment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sensor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sensor.sensor_id", ondelete="RESTRICT"), nullable=False
    )
    station_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("research_station.station_id", ondelete="RESTRICT"), nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    sensor: Mapped["Sensor"] = relationship("Sensor", back_populates="deployments")
    station: Mapped["ResearchStation"] = relationship("ResearchStation", back_populates="deployments")

    __table_args__ = (
        CheckConstraint("end_time IS NULL OR end_time >= start_time", name="chk_deployment_time"),
    )


class Calibration(Base):
    __tablename__ = "calibration"

    calibration_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sensor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sensor.sensor_id", ondelete="RESTRICT"), nullable=False
    )
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    calibration_factor: Mapped[Decimal] = mapped_column(Numeric(10, 5), default=Decimal("1.00000"), nullable=False)
    calibrated_by: Mapped[str] = mapped_column(String(120), nullable=False)
    document_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    sensor: Mapped["Sensor"] = relationship("Sensor", back_populates="calibrations")

    __table_args__ = (
        CheckConstraint("valid_to >= valid_from", name="chk_calibration_dates"),
    )

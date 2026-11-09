import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MobileDevice(Base):
    __tablename__ = "mobile_devices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(unique=True, index=True)
    manufacturer: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str | None] = mapped_column(String(160))
    android_version: Mapped[str | None] = mapped_column(String(80))
    sensor_name: Mapped[str | None] = mapped_column(String(200))
    sensor_vendor: Mapped[str | None] = mapped_column(String(160))
    sensor_resolution: Mapped[float | None] = mapped_column(Float)
    sensor_maximum_range: Mapped[float | None] = mapped_column(Float)
    app_version: Mapped[str | None] = mapped_column(String(80))
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    reports: Mapped[list["SensorReport"]] = relationship(back_populates="device", cascade="all, delete-orphan")


class SensorReport(Base):
    __tablename__ = "sensor_reports"
    __table_args__ = (Index("ix_sensor_reports_device_recorded", "device_id", "recorded_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mobile_devices.device_id", ondelete="CASCADE"), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    duration_ms: Mapped[int] = mapped_column(Integer)
    sample_count: Mapped[int] = mapped_column(Integer)
    sampling_rate_hz: Mapped[float] = mapped_column(Float)
    motion_state: Mapped[str] = mapped_column(String(32))
    peak_acceleration: Mapped[float] = mapped_column(Float)
    rms_acceleration: Mapped[float] = mapped_column(Float)
    sensor_type: Mapped[str] = mapped_column(String(80))

    device: Mapped[MobileDevice] = relationship(back_populates="reports")

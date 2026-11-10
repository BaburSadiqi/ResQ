import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class MotionState(str, Enum):
    NORMAL = "NORMAL"
    MOVEMENT = "MOVEMENT"
    STRONG_VIBRATION = "STRONG_VIBRATION"


class DeviceRegistration(BaseModel):
    device_id: uuid.UUID
    manufacturer: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=160)
    android_version: str | None = Field(default=None, max_length=80)
    sensor_name: str | None = Field(default=None, max_length=200)
    sensor_vendor: str | None = Field(default=None, max_length=160)
    sensor_resolution: float | None = Field(default=None, ge=0, le=10000)
    sensor_maximum_range: float | None = Field(default=None, ge=0, le=100000)
    app_version: str | None = Field(default=None, max_length=80)


class SensorReportCreate(BaseModel):
    device_id: uuid.UUID
    recorded_at: datetime
    duration_ms: int = Field(ge=100, le=60_000)
    sample_count: int = Field(ge=1, le=10_000)
    sampling_rate_hz: float = Field(gt=0, le=1_000)
    motion_state: MotionState
    peak_acceleration: float = Field(ge=0, le=1_000)
    rms_acceleration: float = Field(ge=0, le=1_000)
    sensor_type: str = Field(min_length=1, max_length=80)

    @field_validator("recorded_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at must include a UTC offset")
        return value


class DeviceResponse(BaseModel):
    device_id: uuid.UUID
    manufacturer: str | None
    model: str | None
    android_version: str | None
    sensor_name: str | None
    sensor_vendor: str | None
    app_version: str | None
    registered_at: datetime
    last_seen: datetime
    online: bool
    latest_report: "SensorReportResponse | None" = None


class SensorReportResponse(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    recorded_at: datetime
    received_at: datetime
    duration_ms: int
    sample_count: int
    sampling_rate_hz: float
    motion_state: MotionState
    peak_acceleration: float
    rms_acceleration: float
    sensor_type: str


class RegistrationResponse(BaseModel):
    device_id: uuid.UUID
    registered: bool = True
    last_seen: datetime


class MobileHealthResponse(BaseModel):
    status: str = "ok"
    service: str = "resq-mobile-network"


class CorrelatedVibrationAlert(BaseModel):
    event_id: uuid.UUID
    created_at: datetime
    status: str = "SUSPECTED_SEISMIC_EVENT"
    device_count: int
    participant_device_ids: list[uuid.UUID]
    trigger_timestamps: list[datetime]
    maximum_peak: float
    correlation_window_seconds: float

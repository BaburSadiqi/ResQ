from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TargetLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=80)]
    latitude: Annotated[float, Field(ge=-90, le=90)]
    longitude: Annotated[float, Field(ge=-180, le=180)]

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Target name must contain a non-whitespace character.")
        return value


class EarlyWarningSimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: Annotated[float, Field(ge=-90, le=90, description="Hypothetical epicenter latitude.")]
    longitude: Annotated[
        float, Field(ge=-180, le=180, description="Hypothetical epicenter longitude.")
    ]
    magnitude: Annotated[float, Field(ge=-2, le=10)]
    depth_km: Annotated[float, Field(ge=0, le=700)]
    detection_delay_seconds: Annotated[float, Field(ge=0, le=60)] = 0.8
    processing_delay_seconds: Annotated[float, Field(ge=0, le=60)] = 0.5
    sensor_count: Annotated[int, Field(ge=1, le=20)] = 8
    required_sensor_count: Annotated[int, Field(ge=1, le=20)] = 2
    sensor_radius_km: Annotated[float, Field(gt=0, le=1000)] = 250
    p_wave_velocity_km_s: Annotated[float, Field(ge=3, le=8)] = 6
    s_wave_velocity_km_s: Annotated[float, Field(ge=1.5, le=5)] = 3.5
    targets: Annotated[list[TargetLocation], Field(min_length=1, max_length=8)]

    @model_validator(mode="after")
    def validate_network_and_velocities(self) -> "EarlyWarningSimulationRequest":
        if self.required_sensor_count > self.sensor_count:
            raise ValueError("required_sensor_count cannot exceed sensor_count.")
        if self.p_wave_velocity_km_s <= self.s_wave_velocity_km_s:
            raise ValueError("P-wave velocity must be greater than S-wave velocity.")
        if len({target.name.casefold() for target in self.targets}) != len(self.targets):
            raise ValueError("Target names must be unique.")
        return self


class SimulationModelMetadata(BaseModel):
    name: str
    earth_radius_km: float
    p_wave_velocity_km_s: float
    s_wave_velocity_km_s: float
    detection_delay_seconds: float
    processing_delay_seconds: float
    required_sensor_count: int
    travel_time_formula: str
    sensor_distribution: str
    alert_rule: str
    limitations: list[str]


class SimulatedSensor(BaseModel):
    id: str
    latitude: float
    longitude: float
    epicentral_distance_km: float
    hypocentral_distance_km: float
    p_arrival_seconds: float
    detected_seconds: float
    processed_seconds: float


class TargetWarningResult(BaseModel):
    name: str
    latitude: float
    longitude: float
    epicentral_distance_km: float
    hypocentral_distance_km: float
    p_arrival_seconds: float
    s_arrival_seconds: float
    first_detection_seconds: float
    alert_issuance_seconds: float
    warning_lead_seconds: float
    status: Literal[
        "potential_lead_time", "no_useful_lead_time", "shaking_before_alert"
    ]


class EarlyWarningSimulationResult(BaseModel):
    scenario: EarlyWarningSimulationRequest
    model: SimulationModelMetadata
    first_detection_seconds: float
    alert_issuance_seconds: float
    sensors: list[SimulatedSensor]
    targets: list[TargetWarningResult]
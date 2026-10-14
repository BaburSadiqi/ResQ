from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, HttpUrl, field_validator, model_validator


class UsgsEvent(BaseModel):
    source_event_id: str
    magnitude: Decimal | None
    magnitude_type: str | None
    place: str | None
    latitude: Decimal
    longitude: Decimal
    depth_km: Decimal | None
    occurred_at: datetime
    source_updated_at: datetime | None
    event_type: str | None
    source_status: str | None
    event_url: HttpUrl | None
    raw_properties: dict[str, Any]

    @field_validator("latitude")
    @classmethod
    def latitude_range(cls, value: Decimal) -> Decimal:
        if not -90 <= value <= 90:
            raise ValueError("latitude must be between -90 and 90")
        return value

    @field_validator("longitude")
    @classmethod
    def longitude_range(cls, value: Decimal) -> Decimal:
        if not -180 <= value <= 180:
            raise ValueError("longitude must be between -180 and 180")
        return value

    @model_validator(mode="before")
    @classmethod
    def from_feature(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        properties = value.get("properties") or {}
        geometry = value.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if not value.get("id") or len(coordinates) < 2 or properties.get("time") is None:
            raise ValueError("feature is missing id, coordinates, or time")

        def millis_to_utc(timestamp: int | float | None) -> datetime | None:
            if timestamp is None:
                return None
            return datetime.fromtimestamp(timestamp / 1000, tz=UTC)

        return {
            "source_event_id": value["id"], "magnitude": properties.get("mag"),
            "magnitude_type": properties.get("magType"), "place": properties.get("place"),
            "longitude": coordinates[0], "latitude": coordinates[1],
            "depth_km": coordinates[2] if len(coordinates) > 2 else None,
            "occurred_at": millis_to_utc(properties["time"]),
            "source_updated_at": millis_to_utc(properties.get("updated")),
            "event_type": properties.get("type"), "source_status": properties.get("status"),
            "event_url": properties.get("url"),
            "raw_properties": properties,
        }

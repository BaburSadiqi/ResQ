import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DataSourceRead(BaseModel):
    """Public provenance information for a catalog record."""

    model_config = ConfigDict(from_attributes=True)
    code: str
    name: str


class SeismicEventListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
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
    event_url: str | None
    data_source: DataSourceRead | None = None


class SeismicEventDetail(SeismicEventListItem):
    """The detail representation deliberately excludes raw source payloads."""


SeismicEventRead = SeismicEventDetail


class SeismicEventListQuery(BaseModel):
    limit: Annotated[int, Field(ge=1, le=100)] = 50
    offset: Annotated[int, Field(ge=0)] = 0
    min_magnitude: Annotated[float | None, Field(ge=-2, le=10)] = None
    start_time: datetime | None = None
    end_time: datetime | None = None

    @field_validator("start_time", "end_time")
    @classmethod
    def require_aware_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a UTC offset")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_time_range(self) -> "SeismicEventListQuery":
        if self.start_time and self.end_time and self.start_time > self.end_time:
            raise ValueError("start_time must be before or equal to end_time")
        return self


class SeismicEventPage(BaseModel):
    items: list[SeismicEventListItem]
    limit: int
    offset: int
    total: int

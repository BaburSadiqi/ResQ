import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class SeismicEventRead(BaseModel):
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
    event_status: str | None
    source_url: str | None


class SeismicEventPage(BaseModel):
    items: list[SeismicEventRead]
    limit: int
    offset: int
    total: int

import uuid
from datetime import datetime

from app.models.seismic_event import SeismicEvent
from app.repositories.seismic_event import SeismicEventRepository


class SeismicEventService:
    def __init__(self, repository: SeismicEventRepository) -> None:
        self.repository = repository

    async def list(self, limit: int, offset: int, min_magnitude: float | None, start_time: datetime | None, end_time: datetime | None) -> tuple[list[SeismicEvent], int]:
        return await self.repository.list(limit, offset, min_magnitude, start_time, end_time)

    async def get(self, event_id: uuid.UUID) -> SeismicEvent | None:
        return await self.repository.get(event_id)

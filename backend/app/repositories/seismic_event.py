import uuid
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.seismic_event import SeismicEvent


class SeismicEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self, limit: int, offset: int, min_magnitude: float | None, start_time: datetime | None, end_time: datetime | None
    ) -> tuple[list[SeismicEvent], int]:
        query: Select[tuple[SeismicEvent]] = select(SeismicEvent).options(
            selectinload(SeismicEvent.data_source)
        )
        if min_magnitude is not None:
            query = query.where(SeismicEvent.magnitude >= min_magnitude)
        if start_time is not None:
            query = query.where(SeismicEvent.occurred_at >= start_time)
        if end_time is not None:
            query = query.where(SeismicEvent.occurred_at <= end_time)
        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        rows = await self.session.scalars(query.order_by(SeismicEvent.occurred_at.desc()).limit(limit).offset(offset))
        return list(rows), total or 0

    async def get(self, event_id: uuid.UUID) -> SeismicEvent | None:
        result = await self.session.scalars(
            select(SeismicEvent)
            .options(selectinload(SeismicEvent.data_source))
            .where(SeismicEvent.id == event_id)
        )
        return result.one_or_none()

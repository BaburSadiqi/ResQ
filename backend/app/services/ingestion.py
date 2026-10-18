from datetime import datetime

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.usgs.client import UsgsClient
from app.integrations.usgs.schemas import UsgsEvent
from app.models.data_source import DataSource
from app.models.seismic_event import SeismicEvent


class UsgsIngestionService:
    """Imports finite USGS catalog ranges; catalog entries are not early-warning detections."""
    def __init__(self, session: AsyncSession, client: UsgsClient) -> None:
        self.session, self.client = session, client

    async def ingest(self, start_time: datetime, end_time: datetime, min_magnitude: float | None = None) -> int:
        if start_time.tzinfo is None or start_time.utcoffset() is None:
            raise ValueError("start_time must include a UTC offset")
        if end_time.tzinfo is None or end_time.utcoffset() is None:
            raise ValueError("end_time must include a UTC offset")
        if start_time >= end_time:
            raise ValueError("start_time must be before end_time")
        source = await self.session.scalar(select(DataSource).where(DataSource.code == "usgs"))
        if source is None:
            source = DataSource(name="USGS Earthquake Catalog", code="usgs", base_url=str(self.client.settings.usgs_base_url))
            self.session.add(source)
            await self.session.flush()
        imported = 0
        for feature in await self.client.fetch_events(start_time, end_time, min_magnitude):
            try:
                event = UsgsEvent.model_validate(feature)
            except ValidationError:
                # A bad upstream item must not discard the rest of a bounded import.
                continue
            values = event.model_dump()
            if values["event_url"] is not None:
                values["event_url"] = str(values["event_url"])
            statement = (
                insert(SeismicEvent)
                .values(data_source_id=source.id, **values)
                .on_conflict_do_nothing(constraint="uq_event_source_external_id")
                .returning(SeismicEvent.id)
            )
            inserted = await self.session.scalar(statement)
            if inserted is not None:
                imported += 1
        await self.session.commit()
        return imported

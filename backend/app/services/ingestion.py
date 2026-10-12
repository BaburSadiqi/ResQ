from datetime import datetime

from sqlalchemy import select
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
        source = await self.session.scalar(select(DataSource).where(DataSource.name == "USGS Earthquake Catalog"))
        if source is None:
            source = DataSource(name="USGS Earthquake Catalog", base_url=str(self.client.settings.usgs_base_url), source_type="catalog")
            self.session.add(source)
            await self.session.flush()
        imported = 0
        for feature in await self.client.fetch_events(start_time, end_time, min_magnitude):
            event = UsgsEvent.model_validate(feature)
            existing = await self.session.scalar(select(SeismicEvent).where(SeismicEvent.data_source_id == source.id, SeismicEvent.source_event_id == event.source_event_id))
            if existing is None:
                values = event.model_dump()
                if values["source_url"] is not None:
                    values["source_url"] = str(values["source_url"])
                self.session.add(SeismicEvent(data_source_id=source.id, **values))
                imported += 1
        await self.session.commit()
        return imported

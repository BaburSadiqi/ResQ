import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.seismic_event import SeismicEventRepository
from app.schemas.seismic_event import SeismicEventPage, SeismicEventRead
from app.services.seismic_event import SeismicEventService

router = APIRouter(prefix="/seismic-events", tags=["seismic events"])

def get_service(session: AsyncSession = Depends(get_session)) -> SeismicEventService:
    return SeismicEventService(SeismicEventRepository(session))

@router.get("", response_model=SeismicEventPage)
async def list_events(service: Annotated[SeismicEventService, Depends(get_service)], limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), min_magnitude: float | None = Query(None, ge=-2, le=10), start_time: datetime | None = None, end_time: datetime | None = None) -> SeismicEventPage:
    if start_time and end_time and start_time > end_time:
        raise HTTPException(422, "start_time must be before end_time")
    items, total = await service.list(limit, offset, min_magnitude, start_time, end_time)
    return SeismicEventPage(items=[SeismicEventRead.model_validate(item) for item in items], limit=limit, offset=offset, total=total)

@router.get("/{event_id}", response_model=SeismicEventRead)
async def get_event(event_id: uuid.UUID, service: Annotated[SeismicEventService, Depends(get_service)]) -> SeismicEventRead:
    event = await service.get(event_id)
    if event is None:
        raise HTTPException(404, "seismic event not found")
    return SeismicEventRead.model_validate(event)

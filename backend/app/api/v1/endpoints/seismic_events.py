import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.seismic_event import SeismicEventRepository
from app.schemas.seismic_event import (
    SeismicEventDetail,
    SeismicEventListItem,
    SeismicEventListQuery,
    SeismicEventPage,
)
from app.services.seismic_event import SeismicEventService

router = APIRouter(prefix="/seismic-events", tags=["seismic events"])

def get_service(session: AsyncSession = Depends(get_session)) -> SeismicEventService:
    return SeismicEventService(SeismicEventRepository(session))


def get_list_query(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    min_magnitude: Annotated[float | None, Query(ge=-2, le=10)] = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> SeismicEventListQuery:
    """Translate cross-field Pydantic validation failures into HTTP 422 responses."""
    try:
        return SeismicEventListQuery(
            limit=limit,
            offset=offset,
            min_magnitude=min_magnitude,
            start_time=start_time,
            end_time=end_time,
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


@router.get("", response_model=SeismicEventPage)
async def list_events(
    filters: Annotated[SeismicEventListQuery, Depends(get_list_query)],
    service: Annotated[SeismicEventService, Depends(get_service)],
) -> SeismicEventPage:
    items, total = await service.list(
        filters.limit, filters.offset, filters.min_magnitude, filters.start_time, filters.end_time
    )
    return SeismicEventPage(
        items=[SeismicEventListItem.model_validate(item) for item in items],
        limit=filters.limit,
        offset=filters.offset,
        total=total,
    )

@router.get("/{event_id}", response_model=SeismicEventDetail)
async def get_event(
    event_id: uuid.UUID, service: Annotated[SeismicEventService, Depends(get_service)]
) -> SeismicEventDetail:
    event = await service.get(event_id)
    if event is None:
        raise HTTPException(404, "seismic event not found")
    return SeismicEventDetail.model_validate(event)

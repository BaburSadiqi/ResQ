
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.analytics import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsSummary,
    GeographicAnalyticsSummary,
    GeographicBounds,
    GeographicBoundsQuery,
)
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def get_analytics_service(
    session: AsyncSession = Depends(get_session),
) -> AnalyticsService:
    return AnalyticsService(AnalyticsRepository(session))


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsSummary:
    return await service.get_summary()


def get_geographic_bounds(
    south: Annotated[
        Decimal, Query(ge=-90, le=90, description="Southern latitude, in WGS 84 degrees.")
    ],
    north: Annotated[
        Decimal, Query(ge=-90, le=90, description="Northern latitude, in WGS 84 degrees.")
    ],
    west: Annotated[
        Decimal, Query(ge=-180, le=180, description="Western longitude, in WGS 84 degrees.")
    ],
    east: Annotated[
        Decimal, Query(ge=-180, le=180, description="Eastern longitude, in WGS 84 degrees.")
    ],
) -> GeographicBoundsQuery:
    try:
        return GeographicBoundsQuery(south=south, north=north, west=west, east=east)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


@router.get(
    "/geographic",
    response_model=GeographicAnalyticsSummary,
    summary="Aggregate observed catalog events within a bounding box",
    description=(
        "Returns statistics for stored, already-published catalog events within a WGS 84 "
        "bounding box. If `west` is greater than `east`, the box crosses the antimeridian. "
        "Magnitude statistics exclude null magnitudes; total event counts include them. "
        "These observed catalog aggregates do not predict future earthquakes or establish risk."
    ),
)
async def get_geographic_analytics_summary(
    bounds: Annotated[GeographicBoundsQuery, Depends(get_geographic_bounds)],
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> GeographicAnalyticsSummary:
    summary = await service.get_geographic_summary(
        bounds.south, bounds.north, bounds.west, bounds.east
    )
    return GeographicAnalyticsSummary(
        bounds=GeographicBounds(
            south=bounds.south,
            north=bounds.north,
            west=bounds.west,
            east=bounds.east,
            crosses_antimeridian=bounds.west > bounds.east,
        ),
        **summary,
    )

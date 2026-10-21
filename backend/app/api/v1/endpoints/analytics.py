
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.analytics import AnalyticsRepository
from app.schemas.analytics import AnalyticsSummary
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

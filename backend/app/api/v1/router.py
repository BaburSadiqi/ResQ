from fastapi import APIRouter

from app.api.v1.endpoints import health, seismic_events
from app.api.v1.endpoints.analytics import router as analytics_router


router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(seismic_events.router)
router.include_router(analytics_router)
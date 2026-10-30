from fastapi import APIRouter

from app.api.v1.endpoints import early_warning, health, scenarios, seismic_events
from app.api.v1.endpoints.analytics import router as analytics_router

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(seismic_events.router)
router.include_router(analytics_router)
router.include_router(scenarios.router)
router.include_router(early_warning.router)

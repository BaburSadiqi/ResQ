from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.scenario import ScenarioRepository
from app.schemas.scenario import EarthquakeScenarioRequest, EarthquakeScenarioSimulation
from app.services.scenario import ScenarioService

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


def get_scenario_service(session: AsyncSession = Depends(get_session)) -> ScenarioService:
    return ScenarioService(ScenarioRepository(session))


@router.post(
    "/earthquake",
    response_model=EarthquakeScenarioSimulation,
    summary="Compare a hypothetical earthquake with historical catalog proximity",
    description=(
        "Performs a research-only, read-only comparison between a hypothetical earthquake "
        "location and stored, already-published catalog events. It is not earthquake prediction, "
        "operational early warning, or a validated ground-shaking, casualty, or damage assessment. "
        "The hypothetical scenario is not stored."
    ),
)
async def simulate_earthquake(
    scenario: EarthquakeScenarioRequest,
    service: Annotated[ScenarioService, Depends(get_scenario_service)],
) -> EarthquakeScenarioSimulation:
    historical_catalog = await service.simulate_earthquake(
        scenario.latitude, scenario.longitude, scenario.radius_km
    )
    return EarthquakeScenarioSimulation(
        scenario=scenario,
        historical_catalog=historical_catalog,
    )

from fastapi import APIRouter

from app.schemas.early_warning import (
    EarlyWarningSimulationRequest,
    EarlyWarningSimulationResult,
)
from app.services.early_warning import simulate_early_warning

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


@router.post(
    "/early-warning",
    response_model=EarlyWarningSimulationResult,
    summary="Run a hypothetical earthquake early-warning research simulation",
    description=(
        "Calculates a deterministic, in-memory P/S-wave and synthetic-sensor timeline. "
        "This is a research simulation only, not a real-time warning service or a validated "
        "algorithm."
    ),
)
def simulate_early_warning_scenario(
    scenario: EarlyWarningSimulationRequest,
) -> EarlyWarningSimulationResult:
    return simulate_early_warning(scenario)
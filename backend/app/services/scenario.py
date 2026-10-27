from decimal import Decimal
from typing import Any

from app.repositories.scenario import ScenarioRepository


class ScenarioService:
    def __init__(self, repository: ScenarioRepository) -> None:
        self.repository = repository

    async def simulate_earthquake(
        self, latitude: Decimal, longitude: Decimal, radius_km: Decimal
    ) -> dict[str, Any]:
        return await self.repository.get_historical_proximity_summary(
            latitude, longitude, radius_km
        )
